#!/usr/bin/env python3
# Herdrのtab_bar_rightから60秒毎に起動され、各agentペインのサイドバー用トークンを書く。
#   claude: プロンプトキャッシュの残り時間（claude_cache）
#   codex : 最後の応答完了を起点にした残り時間（codex_last_response）
# 標準出力は常に空（tab_bar_rightはタイマー代わりにだけ使う）。
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ai/codex/hooks"))
from codex_hook_common import find_session_transcript_path

SOURCE = "agent-timers"
# 実行間隔(60秒)の3倍。スクリプトが止まったら3分で表示が消える。
TOKEN_TTL_MS = 180000
# shortcut: TTL is fixed at 1h (subscription default); read CLAUDE_CODE_PROMPT_CACHE_TTL etc. if 5m sessions matter
CACHE_TTL_SECONDS = 3600
# 切れる前に気付いて動けるよう、残りがこれを下回ったら赤にする。
RED_BELOW_SECONDS = 600
# shortcut: 30min is an assumed Codex cache lifetime (matches the old 25/30min colour steps), verify against Codex's real TTL
CODEX_CACHE_TTL_SECONDS = 1800


def session(pane, agent):
    value = pane.get("agent_session") or {}
    return value.get("value") if pane.get("agent") == agent and isinstance(value, dict) else None


def last_completion(session_id):
    path = find_session_transcript_path(session_id)
    if not path:
        return None
    try:
        with open(path, "rb") as log:
            log.seek(0, 2)
            position = log.tell()
            pending = b""
            first = True
            while position:
                size = min(position, 65536)
                position -= size
                log.seek(position)
                parts = (log.read(size) + pending).split(b"\n")
                pending = parts.pop(0) if position else b""
                if first:
                    parts.pop()  # A non-terminated final record may still be written.
                    first = False
                for line in reversed(parts):
                    try:
                        record = json.loads(line)
                        payload = record.get("payload", {})
                        if record.get("type") == "event_msg" and payload.get("type") == "task_complete":
                            value = payload.get("completed_at")
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                datetime.fromtimestamp(value)
                                return value
                    except (ValueError, TypeError, AttributeError, OverflowError, OSError):
                        continue
    except OSError:
        return None
    return None


def cache_last_request(session_id):
    # cache-tools modが永続化する最終リクエスト送信時刻（epoch ms）。非公開形式なので読めなければNone。
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    for path in glob.glob(str(base / "plugins/store/cache-tools_*.json")):
        try:
            with open(path, encoding="utf-8") as store:
                value = json.load(store).get(f"cacheTtl.session.{session_id}").get("lastAt")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value / 1000
    return None


def minutes(seconds):
    hours, mins = divmod(int(seconds // 60), 60)
    return f"{hours}h{mins:02d}m" if hours else f"{mins}m"


def format_remaining(now, base_time, ttl_seconds):
    remaining = ttl_seconds - (now - base_time)
    if remaining <= 0:
        return "🔴⏳失効"
    if remaining < 60:
        return "🔴⏳<1m"
    if remaining < RED_BELOW_SECONDS:
        return f"🔴⏳{minutes(remaining)}"
    color = "🟡" if remaining / ttl_seconds < 0.25 else "🟢"
    return f"{color}⏳{minutes(remaining)}"


# agent -> (token名, 基準時刻の取得, キャッシュTTL秒)
TIMERS = {
    "claude": ("claude_cache", cache_last_request, CACHE_TTL_SECONDS),
    "codex": ("codex_last_response", last_completion, CODEX_CACHE_TTL_SECONDS),
}


def main():
    cli = os.environ.get("HERDR_BIN_PATH") or "herdr"

    def call(*args):
        result = subprocess.run([cli, *args], capture_output=True, check=True, timeout=1)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    panes = call("pane", "list")["result"]["panes"]
    now = time.time()
    for pane in panes:
        agent = pane.get("agent")
        pane_id = pane.get("pane_id")
        if agent not in TIMERS or not pane_id:
            continue
        sid = session(pane, agent)
        if not sid:
            continue
        token, base_time, ttl = TIMERS[agent]
        at = base_time(sid)
        if at is None and not pane.get("tokens", {}).get(token):
            continue
        # 一覧取得後にペインのセッションが入れ替わっていたら書かない。
        if session(call("pane", "get", pane_id)["result"]["pane"], agent) != sid:
            continue
        if at is None:
            call("pane", "report-metadata", pane_id, "--source", SOURCE, "--clear-token", token)
        else:
            call("pane", "report-metadata", pane_id, "--source", SOURCE, "--agent", agent,
                 "--token", f"{token}={format_remaining(now, at, ttl)}", "--ttl-ms", str(TOKEN_TTL_MS))
    print("")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        print("")
