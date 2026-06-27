#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

HOOK_ERROR_LOG="${TMPDIR:-/tmp}/codex-context-alert-error.log"
exec >/dev/null
exec 2>>"${HOOK_ERROR_LOG}"

source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_emoji.conf" 2>/dev/null || true

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
CODEX_HOOK_COMMON="${HOOK_DIR}/codex_hook_common.py"
if [[ ! -f "${CODEX_HOOK_COMMON}" ]]; then
    CODEX_HOOK_COMMON="${SET:-$HOME/Desktop/repository/SettingFiles/}ai/codex/hooks/codex_hook_common.py"
fi

hook_input=$(cat)

if [[ ! -f "${CODEX_HOOK_COMMON}" ]] || ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

session_id=$(printf '%s' "${hook_input}" | jq -r '.session_id // empty' 2>/dev/null)
transcript_path=$(printf '%s' "${hook_input}" | jq -r '.transcript_path // empty' 2>/dev/null)
if [[ -z "${session_id}" && -n "${transcript_path}" && "${transcript_path}" != "null" ]]; then
    session_id=$(basename "${transcript_path}" .jsonl)
fi

ctx_usage_json=$(printf '%s' "${hook_input}" | python3 "${CODEX_HOOK_COMMON}" context-usage 2>>"${HOOK_ERROR_LOG}")
if [[ -z "${ctx_usage_json}" ]] || ! echo "${ctx_usage_json}" | jq -e '.used_pct' >/dev/null 2>&1; then
    exit 0
fi

ctx_used_pct=$(echo "${ctx_usage_json}" | jq -r '.used_pct')
ctx_window=$(echo "${ctx_usage_json}" | jq -r '.model_context_window // empty')
ctx_window_tokens=$(echo "${ctx_usage_json}" | jq -r '.context_window_tokens // empty')

source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/context-alert.zsh" 2>/dev/null || true
if declare -f ctx_alert_evaluate >/dev/null 2>&1; then
    ctx_alert_evaluate "codex" "${session_id}" "${ctx_used_pct}" \
        "${EMOJI_ID_CODEX:-🪷}" "${ctx_window}" "${ctx_window_tokens}" \
        >/dev/null 2>&1 || true
fi
