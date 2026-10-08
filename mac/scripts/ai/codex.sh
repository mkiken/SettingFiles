#!/bin/zsh

source "${Repo}mac/scripts/ai/claude_mem.sh"
source "${Repo}mac/scripts/ai/rtk.sh"

function setup_codex_rtk() {
  echo "Ensuring Codex RTK command support..."

  require_rtk_token_killer
}

function setup_codex_caveman() {
  local caveman_skill="$HOME/.agents/skills/caveman/SKILL.md"

  echo "Ensuring Codex Caveman skill..."

  if [[ -f "$caveman_skill" ]]; then
    echo "✓ Codex Caveman skill already installed."
    return 0
  fi

  npx --yes skills@latest add JuliusBrussee/caveman --agent codex --global --skill caveman --yes || return 1

  if [[ ! -f "$caveman_skill" ]]; then
    echo "Error: Codex Caveman skill was not installed at $caveman_skill" >&2
    return 1
  fi
}

function update_codex_caveman() {
  local caveman_skill="$HOME/.agents/skills/caveman/SKILL.md"

  if [[ ! -f "$caveman_skill" ]]; then
    setup_codex_caveman
    return $?
  fi

  echo "Updating Codex Caveman skill..."
  npx --yes skills@latest update caveman --global --yes || return 1

  if [[ ! -f "$caveman_skill" ]]; then
    echo "Error: Codex Caveman skill disappeared after update: $caveman_skill" >&2
    return 1
  fi
}

function setup_codex_context_mode() {
  echo "Ensuring Codex context-mode plugin..."

  setup_context_mode_cli || return 1
  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  if ! codex plugin marketplace list | /usr/bin/grep -Fq "context-mode"; then
    codex plugin marketplace add mksglu/context-mode || return 1
  fi

  codex plugin marketplace upgrade context-mode >/dev/null 2>&1 || true

  if codex plugin list --json | jq -e '.installed[]? | select(.pluginId == "context-mode@context-mode" or (.name == "context-mode" and .marketplaceName == "context-mode"))' >/dev/null; then
    echo "✓ Codex context-mode plugin already installed."
  else
    codex plugin add context-mode@context-mode || return 1
  fi
}

function setup_codex_superpowers() {
  echo "Ensuring Codex Superpowers plugin..."

  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  if ! codex plugin marketplace list | /usr/bin/grep -Fq "openai-curated"; then
    codex plugin marketplace add openai/plugins || return 1
  fi

  # openai-curated may be a bundled local snapshot; refresh only when the CLI supports it.
  codex plugin marketplace upgrade openai-curated >/dev/null 2>&1 || true

  # codex plugin add には確認スキップフラグが無いため、-y 相当は付けられない。
  # 代わりにインストール済み判定を確実にして add 自体を再実行しない。
  #
  # codex plugin list --json はローカル marketplace(openai-curated) の項目を
  # 返さないため、.installed だけを見る guard は add 成功後も一致せず毎回 add が走る。
  # config.toml の [plugins.'superpowers@openai-curated'] が add の永続的な結果なので、
  # これをフォールバックとして併用する。
  if codex plugin list --json | jq -e '.installed[]? | select(.pluginId == "superpowers@openai-curated" or (.name == "superpowers" and .marketplaceName == "openai-curated"))' >/dev/null \
    || /usr/bin/grep -Fq "[plugins.'superpowers@openai-curated']" "$HOME/.codex/config.toml" 2>/dev/null; then
    echo "✓ Codex Superpowers plugin already installed."
  else
    codex plugin add superpowers@openai-curated || return 1
  fi
}

function setup_codex_claude_mem() {
  echo "Ensuring Codex claude-mem plugin..."

  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  # 既にインストール済みなら npx install を再実行しない。
  # claude-mem のインストーラーは再実行のたびに ~/.codex/config.toml に
  # [plugins.'claude-mem@...'] テーブルを追記するため、二重登録すると不正 TOML になる。
  if codex plugin list --json | jq -e '.installed[]? | select(.name == "claude-mem" or (.pluginId // "" | test("claude-mem")))' >/dev/null; then
    echo "✓ Codex claude-mem plugin already installed."
  else
    setup_claude_mem_for_ide codex-cli || return 1
  fi

  setup_claude_mem_runtime || return 1
}

function setup_codex_ponytail() {
  echo "Ensuring Codex ponytail plugin..."

  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  if ! codex plugin marketplace list | /usr/bin/grep -Fq "ponytail"; then
    codex plugin marketplace add DietrichGebert/ponytail || return 1
  fi

  codex plugin marketplace upgrade ponytail >/dev/null 2>&1 || true

  # ponytail は git 解決される marketplace（openai-curated のような bundled
  # スナップショットではない）なので、context-mode と同様 .installed[] に現れる。
  # codex plugin add には確認スキップフラグが無く、guard を外すと
  # 対話プロンプトで停止するため、この判定を確実にする必要がある。
  if codex plugin list --json | jq -e '.installed[]? | select(.pluginId == "ponytail@ponytail" or (.name == "ponytail" and .marketplaceName == "ponytail"))' >/dev/null; then
    echo "✓ Codex ponytail plugin already installed."
  else
    codex plugin add ponytail@ponytail || return 1
  fi

  # モードは upstream 既定の full に依存する。~/.config/ponytail/config.json は
  # ponytail 自身が書き戻すため、リポジトリからの宣言管理はしない。
  #
  # ponytail の hook は ~/.codex/config.toml の [hooks.state] に trust 済みで
  # ないと動作しない。trust は `codex` 起動後 `/hooks` での対話操作が必要で、
  # 既存の context-mode・claude-mem 同様ここでは自動化しない。
}

function setup_codex_hooks_json() {
  # Orca 等の外部ツールが live の hooks.json へ追記するため、リポジトリへ
  # 書き戻る symlink ではなく実ファイルにして smart_merge_json で取り込む。
  local live="$HOME/.codex/hooks.json"
  local tmp_file=""

  mkdir -p "${live:h}" || return 1
  if [[ -L "$live" ]]; then
    # 旧 symlink 方式からの移行: merge がリンク先(リポジトリ)へ書かないよう実体化
    tmp_file="$(mktemp "${live}.XXXXXX")" || return 1
    if ! /bin/cp "$live" "$tmp_file" || ! /bin/mv -f "$tmp_file" "$live"; then
      [[ -e "$tmp_file" ]] && trash "$tmp_file"
      echo "Error: failed to convert $live from symlink to a regular file" >&2
      return 1
    fi
  fi
  smart_merge_json "${Repo}ai/codex/hooks.json" "$live"
}

function setup_codex_regular_file_agents() {
  # Symlinked config-audit and audit-fix designer startup failed with
  # "Too many levels of symbolic links". Keep these families as regular TOML files.
  python3 - "${Repo}ai/codex/agents" "$HOME/.codex/agents" <<'PYTHON'
import os
from pathlib import Path
import sys
import tempfile
import tomllib

source_dir, dest_dir = map(Path, sys.argv[1:])
roles = {f"config_auditor_{dimension}": "config_audit"
         for dimension in ("default", "conflict", "overlap", "patch", "ambiguity", "concise")}
roles.update({f"audit_fix_{role}": "audit_fix" for role in ("designer", "implementer")})
pending = []
try:
    # Validate every source and destination before replacing any role.
    for role, family in roles.items():
        notice = (f"# GENERATED FILE - do not edit. Sources: ai/common/{family}_subagents/, "
                  f"ai/codex/agents_src/{family}/. Regen: mac/updates/codex.sh.")
        source = source_dir / f"{role}.toml"
        destination = dest_dir / source.name
        content = source.read_bytes()
        tomllib.loads(content.decode("utf-8"))
        if destination.is_symlink():
            if destination.resolve() != source.resolve():
                raise ValueError(f"Unexpected agent symlink: {destination}")
        elif destination.exists():
            if not destination.is_file():
                raise ValueError(f"Unexpected agent destination: {destination}")
            existing = destination.read_bytes()
            if existing == content:
                continue
            if not existing.decode("utf-8").startswith(notice + "\n"):
                raise ValueError(f"Unexpected agent file: {destination}")
            tomllib.loads(existing.decode("utf-8"))
        pending.append((destination, content))
    dest_dir.mkdir(parents=True, exist_ok=True)
    for destination, content in pending:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False) as output:
                temporary = Path(output.name)
                output.write(content)
            os.replace(temporary, destination)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
except (OSError, UnicodeError, ValueError) as error:
    print(f"Error: cannot install Codex regular-file agents: {error}", file=sys.stderr)
    sys.exit(1)
PYTHON
}
