#!/bin/bash
# AI通知フック3本（claude/codex/gemini）の手動スモークテスト。
# 各フックへ代表イベントのhook JSONを投入し、exit codeを検証する。
# 実行すると実際のMac通知とtmuxウィンドウアイコン変更が発生するため、
# unittestの自動discover対象外（tests/manual/）に置く手動実行専用。
# Usage: bash tests/manual/notification_hook_smoke.sh

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap '/bin/rm -rf "${WORK_DIR}"' EXIT

# 1ケース実行: stdinへhook JSONを投入し、exit 0ならPASS
# Usage: run_case <label> <hook_path> <input_json> [hook_args...]
run_case() {
    local label="$1" hook="$2" input="$3"
    shift 3
    local status=0
    printf '%s' "${input}" | bash "${hook}" "$@" || status=$?
    if [[ ${status} -eq 0 ]]; then
        echo "PASS: ${label}"
        return 0
    fi
    echo "FAIL: ${label} (exit=${status})"
    return 1
}

main() {
    local failures=0
    local claude_hook="${REPO_ROOT}/ai/claude/hooks/stop-send-notification.sh"
    local codex_hook="${REPO_ROOT}/ai/codex/hooks/codex-stop-notification.sh"
    local gemini_hook="${REPO_ROOT}/ai/gemini/hooks/notification.sh"

    # --- フィクスチャ生成 ---
    local claude_transcript="${WORK_DIR}/smoke-claude.jsonl"
    cat > "${claude_transcript}" <<'EOF'
{"timestamp":"2026-07-11T12:00:00.000Z","message":{"role":"user","content":"通知フックのスモークテストを実行して"},"isSidechain":false}
{"timestamp":"2026-07-11T12:05:30.000Z","message":{"role":"assistant","content":[{"type":"text","text":"完了しました"}]}}
EOF

    # Codexのrolloutは response_item イベント（payload.content の input_text / output_text）形式
    local codex_transcript="${WORK_DIR}/smoke-codex.jsonl"
    cat > "${codex_transcript}" <<'EOF'
{"timestamp":"2026-07-11T12:00:00.000Z","type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"/pr-review 123 をテスト"}]}}
{"timestamp":"2026-07-11T12:03:00.000Z","type":"response_item","payload":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"レビュー完了"}]}}
EOF

    # Geminiは .../<uuid>/transcript.json 形式（session_id無し入力でparent-dir導出も踏む）
    local gemini_dir="${WORK_DIR}/smoke-gemini-uuid-1234"
    mkdir -p "${gemini_dir}"
    local gemini_transcript="${gemini_dir}/transcript.json"
    cat > "${gemini_transcript}" <<'EOF'
{"startTime":"2026-07-11T12:00:00.000Z","lastUpdated":"2026-07-11T12:02:00.000Z","messages":[{"type":"user","content":"設定を確認して"},{"type":"gemini","content":"確認しました"}]}
EOF

    # --- 各フック×代表イベント ---
    run_case "claude Stop" "${claude_hook}" \
        "{\"hook_event_name\":\"Stop\",\"transcript_path\":\"${claude_transcript}\",\"session_id\":\"smoke-claude\"}" \
        || failures=$((failures + 1))
    run_case "claude Notification (permission_prompt)" "${claude_hook}" \
        "{\"hook_event_name\":\"Notification\",\"notification_type\":\"permission_prompt\",\"message\":\"Bashの実行を許可しますか？\",\"transcript_path\":\"${claude_transcript}\",\"session_id\":\"smoke-claude\"}" \
        || failures=$((failures + 1))

    run_case "codex PermissionRequest" "${codex_hook}" \
        "{\"hook_event_name\":\"PermissionRequest\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ls -la\\ngit status\"},\"transcript_path\":\"${codex_transcript}\",\"session_id\":\"smoke-codex\"}" \
        || failures=$((failures + 1))
    run_case "codex Stop" "${codex_hook}" \
        "{\"hook_event_name\":\"Stop\",\"transcript_path\":\"${codex_transcript}\",\"session_id\":\"smoke-codex\"}" \
        || failures=$((failures + 1))

    run_case "gemini after_agent" "${gemini_hook}" \
        "{\"transcript_path\":\"${gemini_transcript}\"}" \
        --event after_agent || failures=$((failures + 1))
    run_case "gemini notification (ToolPermission)" "${gemini_hook}" \
        "{\"notification_type\":\"ToolPermission\",\"details\":{\"tool_name\":\"run_shell_command\",\"tool_input\":{\"command\":\"ls -la\"}},\"transcript_path\":\"${gemini_transcript}\"}" \
        --event notification || failures=$((failures + 1))

    echo "----"
    if [[ ${failures} -eq 0 ]]; then
        echo "all smoke cases passed"
    else
        echo "${failures} case(s) failed"
        exit 1
    fi
}

main "$@"
