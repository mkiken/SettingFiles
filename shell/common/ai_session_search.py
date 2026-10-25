#!/usr/bin/env python3
"""Claude Code / Codex / Gemini CLI の会話履歴を横断して全文検索する（`ais` のバックエンド）。

サブコマンド:
  list                         全セッションを新しい順に TSV で出力
  search <query>               本文（user/assistant のテキスト）に全語を含むセッションだけ出力
  preview <agent> <file> [q]   fzf プレビュー用に会話を整形して出力

TSV 列: agent, session_id, cwd, file, 表示文字列
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

AGENTS = ("claude", "codex", "gemini")
ICONS = {"claude": "CL", "codex": "CX", "gemini": "GM"}

# harness が user ロールで注入するメッセージ（<environment_context> 等）を本文から除く。
# 先頭がタグ形式で始まる実ユーザー発話も落ちるが、検索・表示への影響は小さいので許容する。
_INJECTED_RE = re.compile(r"\s*(<[A-Za-z][\w\-]*[ >]|# AGENTS\.md instructions)")

# gemini の a2a-server が書く内部ログ。user 発話が無く `--resume` でも選べず、実測で
# 604 ファイル中 585 を占めるため、全件パースする前にメタ行だけで除外する。
_GEMINI_A2A_SESSION_ID = "a2a-server"

_PREVIEW_MESSAGE_LIMIT = 3000
_MATCH_START, _MATCH_END = "\x1b[1;33m", "\x1b[0m"


@dataclass
class Session:
    agent: str
    sid: str
    cwd: str
    path: Path
    mtime: float
    title: str = ""


def _env_root(name, default):
    value = os.environ.get(name)
    return Path(value) if value else Path.home() / default


def roots():
    gemini_home = os.environ.get("GEMINI_CLI_HOME")
    return {
        "claude": _env_root("CLAUDE_CONFIG_DIR", ".claude") / "projects",
        "codex": _env_root("CODEX_HOME", ".codex") / "sessions",
        "gemini": (Path(gemini_home) if gemini_home else Path.home()) / ".gemini" / "tmp",
    }


def discover(agent):
    root = roots()[agent]
    if agent == "claude":
        paths = root.glob("*/*.jsonl")
    elif agent == "codex":
        paths = root.rglob("rollout-*.jsonl")
    else:
        paths = (p for pattern in ("*/chats/session-*.json", "*/chats/session-*.jsonl") for p in root.glob(pattern))
    return sorted(paths)


def _jsonl(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


def _blocks_text(content, kinds):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and (kinds is None or block.get("type") in kinds)
    ]
    return "\n".join(part for part in parts if isinstance(part, str))


def _keep(role, text):
    if not text.strip():
        return False
    return not (role == "user" and _INJECTED_RE.match(text))


def claude_messages(path):
    for obj in _jsonl(path):
        role = obj.get("type")
        if role not in ("user", "assistant") or obj.get("isSidechain") or obj.get("isMeta"):
            continue
        message = obj.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        text = _blocks_text(content, ("text",))
        if _keep(role, text):
            yield role, text


def codex_messages(path):
    for obj in _jsonl(path):
        payload = obj.get("payload")
        if obj.get("type") != "response_item" or not isinstance(payload, dict):
            continue
        role = payload.get("role")
        if payload.get("type") != "message" or role not in ("user", "assistant"):
            continue
        text = _blocks_text(payload.get("content"), ("input_text", "output_text"))
        if _keep(role, text):
            yield role, text


def _gemini_raw_messages(path):
    """`.json` は messages 配列、`.jsonl` は最後の `$set.messages` と後続の単独行（id で重複排除）。"""
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            return []
        messages = data.get("messages", []) if isinstance(data, dict) else []
        return [m for m in messages if isinstance(m, dict)]
    messages = []
    for obj in _jsonl(path):
        if "$set" in obj:
            replaced = obj["$set"].get("messages") if isinstance(obj["$set"], dict) else None
            if isinstance(replaced, list):
                messages = [m for m in replaced if isinstance(m, dict)]
        elif "type" in obj and "id" in obj:
            messages.append(obj)
    seen, unique = set(), []
    for message in messages:
        key = message.get("id")
        if key is None or key not in seen:
            seen.add(key)
            unique.append(message)
    return unique


def gemini_messages(path):
    for message in _gemini_raw_messages(path):
        role = {"user": "user", "gemini": "assistant"}.get(message.get("type"))
        if role is None:
            continue
        text = _blocks_text(message.get("content"), None)
        if _keep(role, text):
            yield role, text


MESSAGE_READERS = {"claude": claude_messages, "codex": codex_messages, "gemini": gemini_messages}


def gemini_project_dirs():
    """projectHash（プロジェクト絶対パスの sha256）から cwd を逆引きする表。"""
    gemini_home = os.environ.get("GEMINI_CLI_HOME")
    projects_file = (Path(gemini_home) if gemini_home else Path.home()) / ".gemini" / "projects.json"
    try:
        data = json.loads(projects_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    projects = data.get("projects", {}) if isinstance(data, dict) else {}
    return {hashlib.sha256(p.encode()).hexdigest(): p for p in projects}


def _first_user_text(messages):
    for role, text in messages:
        if role == "user":
            return text
    return None


def _claude_session(path):
    cwd = ""
    for obj in _jsonl(path):
        if isinstance(obj.get("cwd"), str):
            cwd = obj["cwd"]
            break
    return path.stem, cwd, _first_user_text(claude_messages(path))


def _codex_session(path):
    sid = cwd = ""
    for obj in _jsonl(path):
        if obj.get("type") == "session_meta" and isinstance(obj.get("payload"), dict):
            sid, cwd = obj["payload"].get("id", ""), obj["payload"].get("cwd", "")
        break
    return sid, cwd, _first_user_text(codex_messages(path))


def _gemini_session(path, project_dirs):
    meta = {}
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            meta = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            pass
    else:
        meta = next(_jsonl(path), {})
    sid = meta.get("sessionId", "")
    if sid == _GEMINI_A2A_SESSION_ID:
        return "", "", None
    cwd = project_dirs.get(meta.get("projectHash", ""), "")
    return sid, cwd, _first_user_text(gemini_messages(path))


def load_session(agent, path, project_dirs=None):
    """user 発話を持たない・ID を持たないファイルは None（resume 対象外）。"""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    if agent == "claude":
        sid, cwd, title = _claude_session(path)
    elif agent == "codex":
        sid, cwd, title = _codex_session(path)
    else:
        sid, cwd, title = _gemini_session(path, gemini_project_dirs() if project_dirs is None else project_dirs)
    if not sid or title is None:
        return None
    return Session(agent, sid, cwd, path, mtime, " ".join(title.split()))


def _short_cwd(cwd):
    home = str(Path.home())
    if cwd == home:
        return "~"
    if cwd.startswith(home + "/"):
        cwd = "~" + cwd[len(home):]
    return cwd if len(cwd) <= 32 else "…" + cwd[-31:]


def format_row(session, extra=""):
    stamp = datetime.fromtimestamp(session.mtime).strftime("%Y-%m-%d %H:%M")
    title = session.title[:100]
    display = f"{stamp}  {ICONS[session.agent]}  {_short_cwd(session.cwd):<32}  {title}{extra}"
    fields = (session.agent, session.sid, session.cwd, str(session.path), display)
    return "\t".join(field.replace("\t", " ").replace("\n", " ") for field in fields)


def all_paths():
    return [(agent, path) for agent in AGENTS for path in discover(agent)]


def list_sessions(paths=None):
    project_dirs = gemini_project_dirs()
    sessions = (load_session(agent, path, project_dirs) for agent, path in (paths or all_paths()))
    return sorted((s for s in sessions if s), key=lambda s: s.mtime, reverse=True)


def _escaped(term):
    """生ファイル上の表現（JSON エスケープ済み・非 ASCII は生 UTF-8）で rg に渡す。"""
    return json.dumps(term, ensure_ascii=False)[1:-1]


def prefilter(terms):
    """最も長い語を含む生ファイルだけに絞る。rg が無ければ全件を候補にする。"""
    paths = all_paths()
    rg = shutil.which("rg")
    if rg is None:
        return paths
    existing = [str(root) for root in roots().values() if root.exists()]
    if not existing:
        return []
    needle = _escaped(max(terms, key=len))
    result = subprocess.run(
        [rg, "-l", "-i", "-F", "--no-config", "-e", needle, "--", *existing],
        capture_output=True,
        text=True,
        check=False,
    )
    hits = set(result.stdout.splitlines())
    return [(agent, path) for agent, path in paths if str(path) in hits]


def _snippet(text, term):
    index = text.casefold().find(term.casefold())
    if index < 0:
        return ""
    start = max(0, index - 20)
    return " ".join(text[start : index + len(term) + 40].split())


def search(query):
    terms = query.split()
    if not terms:
        return [format_row(s) for s in list_sessions()]
    project_dirs = gemini_project_dirs()
    found = []
    for agent, path in prefilter(terms):
        session = load_session(agent, path, project_dirs)
        if session is None:
            continue
        texts = [text for _, text in MESSAGE_READERS[agent](path)]
        folded = "\n".join(texts).casefold()
        if not all(term.casefold() in folded for term in terms):
            continue
        snippet = next((_snippet(t, terms[0]) for t in texts if terms[0].casefold() in t.casefold()), "")
        found.append((session, f"  | …{snippet}…" if snippet else ""))
    found.sort(key=lambda item: item[0].mtime, reverse=True)
    return [format_row(session, extra) for session, extra in found]


def _highlight(text, terms):
    for term in terms:
        text = re.sub(re.escape(term), lambda m: f"{_MATCH_START}{m.group(0)}{_MATCH_END}", text, flags=re.IGNORECASE)
    return text


def preview(agent, file, query=""):
    """query があれば該当メッセージだけ、無ければ会話の先頭から整形する。"""
    terms = query.split()
    lines = []
    for role, text in MESSAGE_READERS[agent](Path(file)):
        if terms and not any(term.casefold() in text.casefold() for term in terms):
            continue
        label = "User" if role == "user" else "Assistant"
        body = text if len(text) <= _PREVIEW_MESSAGE_LIMIT else text[:_PREVIEW_MESSAGE_LIMIT] + "\n…(truncated)"
        lines.append(f"── {label} ──\n{_highlight(body, terms)}\n")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2 or argv[1] not in ("list", "search", "preview"):
        print(__doc__, file=sys.stderr)
        return 2
    command, args = argv[1], argv[2:]
    if command == "list":
        output = [format_row(s) for s in list_sessions()]
    elif command == "search":
        output = search(" ".join(args))
    else:
        if len(args) < 2 or args[0] not in AGENTS:
            print("usage: preview <claude|codex|gemini> <file> [query]", file=sys.stderr)
            return 2
        sys.stdout.write(preview(args[0], args[1], " ".join(args[2:])))
        return 0
    sys.stdout.write("".join(f"{line}\n" for line in output))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except BrokenPipeError:
        sys.exit(0)
