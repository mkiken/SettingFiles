#!/usr/bin/env zsh
# context-alert.zsh — AI context残量アラート共通エンジン
#
# Usage (from hook scripts / statusline):
#   source this file, then call:
#     ctx_alert_evaluate <ai> <session_id> <used_pct> <ai_identifier_emoji> [<window_size>] [<context_window_tokens>]
#
# Parameters:
#   ai                 — "claude" | "codex" | "gemini" (state ファイル区別用)
#   session_id         — セッションID（空文字なら "unknown" で代替）
#   used_pct           — context使用率（整数 0–100）
#   ai_identifier_emoji — 通知タイトル用識別子絵文字 (例: $EMOJI_ID_CLAUDE)
#   window_size        — (省略可) context window サイズ（トークン数、表示用のみ）
#   context_window_tokens — (省略可) 現在のcontext window内トークン数（表示用）
#
# 依存: notify(), build_notification_title() が source 済みであること。
# 未 source の場合は自動ロードを試みる。

# --- 依存の自動ロード（未定義の場合） ---
_CTX_ALERT_SET="${SET:-$HOME/Desktop/repository/SettingFiles/}"
if ! declare -f notify >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    source "${_CTX_ALERT_SET}shell/zsh/alias/notification.zsh" 2>/dev/null || true
fi
if ! declare -f build_notification_title >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    source "${_CTX_ALERT_SET}shell/tmux/tmux_notification_title.sh" 2>/dev/null || true
fi
# 絵文字定数が未定義の場合もロード
if [[ -z "${EMOJI_ID_CLAUDE}" ]]; then
    # shellcheck source=/dev/null
    source "${_CTX_ALERT_SET}shell/tmux/tmux_emoji.conf" 2>/dev/null || true
fi
if ! declare -f add_tmux_context_alert_badge >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    source "${_CTX_ALERT_SET}shell/tmux/tmux_window_name.sh" 2>/dev/null || true
fi

# --- 設定定数（変数で調整可能） ---
_CTX_ALERT_STATE_DIR="${TMPDIR:-/tmp}/ai-context-alert"
_CTX_ALERT_RETENTION_DAYS=7   # state ファイルをN日後に削除
_CTX_ALERT_RESET_MARGIN=20    # used% がこれ以上急減したらフラグリセット
_CTX_ALERT_THRESHOLD_WARN=70  # 残30%（使用率70%）
_CTX_ALERT_THRESHOLD_CRIT=85  # 残15%（使用率85%）

# --- state ファイルパス ---
_ctx_alert_state_path() {
    local ai="$1"
    local session_id="${2:-unknown}"
    # session_idのスラッシュや特殊文字をアンダースコアに変換
    local safe_id="${session_id//[^a-zA-Z0-9._-]/_}"
    echo "${_CTX_ALERT_STATE_DIR}/${ai}-${safe_id}.state"
}

# --- 古い state ファイルを削除 ---
_ctx_alert_cleanup() {
    [[ -d "${_CTX_ALERT_STATE_DIR}" ]] || return 0
    find "${_CTX_ALERT_STATE_DIR}" -name '*.state' -type f \
        -mtime +"${_CTX_ALERT_RETENTION_DAYS}" -delete 2>/dev/null || true
}

# --- state 読み込み ---
# 出力: "<fired_stage> <last_used_pct>"（ファイルが無ければ "0 0"）
_ctx_alert_read_state() {
    local state_file="$1"
    if [[ -f "${state_file}" ]]; then
        cat "${state_file}" 2>/dev/null || echo "0 0"
    else
        echo "0 0"
    fi
}

# --- state 書き込み ---
_ctx_alert_write_state() {
    local state_file="$1"
    local fired_stage="$2"
    local last_used_pct="$3"
    mkdir -p "${_CTX_ALERT_STATE_DIR}" 2>/dev/null
    echo "${fired_stage} ${last_used_pct}" > "${state_file}" 2>/dev/null || true
}

# --- tmux: display-message でバナー通知（window名は変えない） ---
_ctx_alert_tmux_banner() {
    local message="$1"
    local duration="${2:-3000}"  # ミリ秒
    [[ -z "${TMUX_PANE}" || "${TERM_PROGRAM:-}" != "tmux" ]] && return 0
    tmux display-message -d "${duration}" "${message}" 2>/dev/null || true
}

_ctx_alert_add_badge() {
    if declare -f add_tmux_context_alert_badge >/dev/null 2>&1; then
        add_tmux_context_alert_badge >/dev/null 2>&1 || true
    fi
}

_ctx_alert_remove_badge() {
    if declare -f remove_tmux_context_alert_badge >/dev/null 2>&1; then
        remove_tmux_context_alert_badge >/dev/null 2>&1 || true
    fi
}

# --- メイン: context逼迫アラート判定・発火 ---
# Usage: ctx_alert_evaluate <ai> <session_id> <used_pct> <ai_identifier_emoji> [<window_size>] [<context_window_tokens>]
ctx_alert_evaluate() {
    local ai="$1"
    local session_id="${2:-unknown}"
    local used_pct_raw="$3"
    local ai_emoji="$4"
    local window_size="${5:-}"
    local context_window_tokens="${6:-}"

    # 整数に変換（小数点切り捨て）
    local used_pct
    used_pct=$(printf '%.0f' "${used_pct_raw}" 2>/dev/null) || return 0
    # 範囲チェック（0–100以外は何もしない）
    [[ "${used_pct}" -ge 0 && "${used_pct}" -le 100 ]] 2>/dev/null || return 0

    # 古い state ファイルを掃除（毎回軽量に実行）
    _ctx_alert_cleanup

    local state_file
    state_file=$(_ctx_alert_state_path "${ai}" "${session_id}")

    # state 読み込み
    local state_line
    state_line=$(_ctx_alert_read_state "${state_file}")
    local fired_stage last_used_pct
    fired_stage="${state_line%% *}"
    last_used_pct="${state_line##* }"
    # デフォルト値ガード
    fired_stage="${fired_stage:-0}"
    last_used_pct="${last_used_pct:-0}"

    # --- 急減リセット判定 ---
    # 前回のused%が記録済み（0より大）で、今回が大幅に下がっていたらフラグリセット
    if [[ "${last_used_pct}" -gt 0 ]] 2>/dev/null; then
        local drop=$(( last_used_pct - used_pct ))
        if [[ "${drop}" -ge "${_CTX_ALERT_RESET_MARGIN}" ]] 2>/dev/null; then
            fired_stage=0
        fi
    fi

    local remaining=$(( 100 - used_pct ))

    if [[ "${used_pct}" -ge "${_CTX_ALERT_THRESHOLD_WARN}" ]] 2>/dev/null; then
        _ctx_alert_add_badge
    else
        _ctx_alert_remove_badge
        fired_stage=0
    fi

    # --- 通知メッセージ用テキスト生成 ---
    _ctx_alert_fire() {
        local threshold_label="$1"   # "30%" or "15%"
        local notification_group="ctxalert-${ai}-${session_id}"

        local body
        if [[ -n "${window_size}" && "${window_size}" -gt 0 ]] 2>/dev/null; then
            # トークン数も表示
            local used_tokens="${context_window_tokens}"
            if ! [[ -n "${used_tokens}" && "${used_tokens}" -ge 0 ]] 2>/dev/null; then
                used_tokens=$(( used_pct * window_size / 100 ))
            fi
            local used_fmt window_fmt
            if [[ "${window_size}" -ge 1000000 ]]; then
                window_fmt="$(echo "scale=1; ${window_size} / 1000000" | bc)M"
            elif [[ "${window_size}" -ge 1000 ]]; then
                window_fmt="$(echo "scale=1; ${window_size} / 1000" | bc)k"
            else
                window_fmt="${window_size}"
            fi
            if [[ "${used_tokens}" -ge 1000000 ]]; then
                used_fmt="$(echo "scale=1; ${used_tokens} / 1000000" | bc)M"
            elif [[ "${used_tokens}" -ge 1000 ]]; then
                used_fmt="$(echo "scale=1; ${used_tokens} / 1000" | bc)k"
            else
                used_fmt="${used_tokens}"
            fi
            body="🧠 context残り${remaining}% (${used_fmt}/${window_fmt} 使用)"
        else
            body="🧠 context残り${remaining}% (${used_pct}%使用)"
        fi

        # Mac通知（sourcされたnotify関数を使用。stdoutは汚さない）
        if declare -f notify >/dev/null 2>&1; then
            notify "$(build_notification_title "⚠️" "${ai}残り${threshold_label}" "${ai_emoji}")" \
                "${body}" "Tink" "${notification_group}" >/dev/null 2>&1 || true
        fi

        # tmux バナー（bash/zsh 両対応で大文字化）
        local ai_upper
        ai_upper=$(echo "${ai}" | tr '[:lower:]' '[:upper:]')
        _ctx_alert_tmux_banner "⚠️ ${ai_upper} context残り${threshold_label}"
    }

    # --- 閾値判定（残15% = used_pct >= 85 を先に判定） ---
    if [[ "${used_pct}" -ge "${_CTX_ALERT_THRESHOLD_CRIT}" ]] 2>/dev/null; then
        if [[ "${fired_stage}" -lt 85 ]] 2>/dev/null; then
            _ctx_alert_fire "15%"
            fired_stage=85
        fi
    elif [[ "${used_pct}" -ge "${_CTX_ALERT_THRESHOLD_WARN}" ]] 2>/dev/null; then
        if [[ "${fired_stage}" -lt 70 ]] 2>/dev/null; then
            _ctx_alert_fire "30%"
            fired_stage=70
        fi
    fi

    # used% を常に更新して書き戻す（発火の有無に関わらず）
    _ctx_alert_write_state "${state_file}" "${fired_stage}" "${used_pct}"
}
