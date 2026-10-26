#!/bin/zsh

# 通知を無効化するコマンドのリスト
export NOTIFY_COMMAND_EXCLUDE=(
  ais
  ccexp
  ccresume
  cc-search
  ccusage
  claude
  g-delete-branch-not-in-remote-interactive
  gemini
  h
  herdr
  less
  nvim
  ssh
  tail
  top
  vi
  vim
  vimdiff
)

# 長時間実行コマンドの通知設定
# コマンド実行開始時間を記録
_cmd_start_time=0
_cmd_name=""
# 完了✅/失敗❌アイコンがtmux/Herdrに付いている間だけ立てるフラグ（次コマンドの
# preexecで外す際の目印。未設定時は何もしない）
_shell_status_icon_active=""

# 画面停止監視（Herdr専用）: コマンド実行中（preexec〜precmd）にペインの可視画面を
# 定期的に読み、HERDR_IDLE_WATCH_SECONDS（既定180、0で無効）秒変化しなければ⏸️を出す。
# pidfileはペイン単位（<pane_id>が持ち主のPID、<pane_id>.shownは⏸️を出した印）。
zmodload -F zsh/system p:sysparams 2>/dev/null
_HERDR_IDLE_WATCH_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/herdr-idle-watch"
# このシェルが起動した監視のPID。precmdで自分の分だけ止めるため、_cmd_start_timeと
# 同じくpreexec→precmd間で持ち回る。
_herdr_idle_watch_pid=""

# NOTIFY_COMMAND_EXCLUDEに含まれるコマンドか（先頭語のbasenameで判定）
function _notification_is_excluded_command() {
  local cmd_name="${1%% *}"
  cmd_name="${cmd_name##*/}"
  (( ${NOTIFY_COMMAND_EXCLUDE[(Ie)$cmd_name]} ))
}

# ⏸️の付与/除去に使うherdr_status_icon.shを読み込む（未読込・旧版読込済みの両方に対応）
function _herdr_idle_watch_load_icon_lib() {
  (( ${+functions[update_herdr_status_icon]} && ${+functions[remove_herdr_idle_status_icon]} )) && return 0
  source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/herdr/herdr_status_icon.sh" 2>/dev/null || true
}

# 表示フラグを消し、現tabのマーカーが⏸️のときだけアイコンを外す（✋は触らない）
function _herdr_idle_watch_hide() {
  /bin/unlink "${1}.shown" 2>/dev/null
  _herdr_idle_watch_load_icon_lib
  if (( ${+functions[remove_herdr_idle_status_icon]} )); then
    remove_herdr_idle_status_icon || true
  fi
  return 0
}

# 監視ループ（バックグラウンドで実行）。親シェルの死亡・pidfileの持ち主交代・
# `herdr pane read`失敗のいずれかで終了する。
# Usage: _herdr_idle_watch <親シェルPID> <コマンド行> <pidfile> <閾値秒> <間隔秒>
function _herdr_idle_watch() {
  local parent_pid="$1" cmd_line="$2" pidfile="$3" threshold="$4" interval="$5"
  local self_pid="${sysparams[pid]:-}"
  # ループ内でlocalを宣言しない（zshのlocalは再宣言で現在値を出力するため）
  local owner="" screen="" sum="" last_sum="" info="" fields="" agent="" focused=""
  local shown="" notified="" tab_id=""
  local same_since=$SECONDS

  while true; do
    sleep "$interval"
    kill -0 "$parent_pid" 2>/dev/null || break
    read -r owner < "$pidfile" 2>/dev/null
    [[ -n "$self_pid" && "$owner" == "$self_pid" ]] || break

    screen="$(herdr pane read "$HERDR_PANE_ID" --source visible 2>/dev/null)" || break
    sum="$(print -r -- "$screen" | cksum)"
    if [[ "$sum" != "$last_sum" ]]; then
      last_sum="$sum"
      same_since=$SECONDS
      notified=""
      if [[ -n "$shown" ]]; then
        _herdr_idle_watch_hide "$pidfile"
        shown=""
      fi
      continue
    fi
    (( SECONDS - same_since >= threshold )) || continue

    # 閾値超過後だけペイン情報を引く（AI検出済み・フォーカス中は出さない）
    info="$(herdr pane get "$HERDR_PANE_ID" 2>/dev/null)" || break
    fields="$(print -r -- "$info" | jq -r '[(.result.pane.agent // ""), ((.result.pane.focused // false) | tostring)] | join(" ")' 2>/dev/null)" || break
    agent="${fields%% *}"
    focused="${fields##* }"
    # AIペインの入力待ちはnotify-richの✋が担当する
    [[ -n "$agent" ]] && continue
    # 表示中のタブは見ればわかるので出さない（外れたら次周で出す）
    if [[ "$focused" == true ]]; then
      if [[ -n "$shown" ]]; then
        _herdr_idle_watch_hide "$pidfile"
        shown=""
      fi
      continue
    fi
    [[ -n "$shown" ]] && continue

    _herdr_idle_watch_load_icon_lib
    # 同tabで✋（確実な入力待ち）が立っていれば譲る
    tab_id="$(_herdr_resolve_tab_id)"
    [[ "$(_herdr_shell_status_marker_read "$tab_id")" == "${EMOJI_STATUS_NOTIFICATION}" ]] && continue

    # フラグは先に立てる: 表示途中でprecmdに止められても⏸️の後始末が漏れない
    : > "${pidfile}.shown"
    shown=1
    if [[ -z "$notified" ]]; then
      notify --tmux-icon "${EMOJI_STATUS_IDLE}" "${EMOJI_STATUS_IDLE} 画面停止" "${cmd_line} (${threshold}s 画面変化なし)" || true
      notified=1
    else
      update_herdr_status_icon "${EMOJI_STATUS_IDLE}" || true
    fi
    # 表示中にprecmdが先行して持ち主が替わっていたら、自分の⏸️を外して終了
    read -r owner < "$pidfile" 2>/dev/null
    if [[ "$owner" != "$self_pid" ]]; then
      _herdr_idle_watch_hide "$pidfile"
      return 0
    fi
  done

  # 自分がpidfileの持ち主のまま終わる場合（親シェル死亡・read失敗）だけ後始末する
  read -r owner < "$pidfile" 2>/dev/null
  if [[ -n "$self_pid" && "$owner" == "$self_pid" ]]; then
    /bin/unlink "$pidfile" 2>/dev/null
    [[ -f "${pidfile}.shown" ]] && _herdr_idle_watch_hide "$pidfile"
  fi
  return 0
}

# コマンド実行前に監視を起動する。対象外: Herdr外・tmux内・通知無効・閾値0・
# シェル起動（内側シェルのプロンプト待機を誤検知するため。内側のコマンドは内側の
# シェルが監視する）・NOTIFY_COMMAND_EXCLUDE。
function _herdr_idle_watch_start() {
  local cmd_line="$1"
  [[ -n "${HERDR_PANE_ID:-}" && -z "${TMUX:-}" ]] || return 0
  [[ -z "${DISABLE_NOTIFY:-}${NOTIFY_SILENT:-}${_DISABLE_NOTIFY_FOR_CURRENT_CMD:-}" ]] || return 0
  local threshold="${HERDR_IDLE_WATCH_SECONDS:-180}"
  [[ "$threshold" == <-> ]] && (( threshold > 0 )) || return 0
  (( ${+commands[herdr]} )) || return 0

  local first_word="${cmd_line%% *}"
  first_word="${first_word##*/}"
  case "$first_word" in
    zsh|bash|sh|fish) return 0 ;;
  esac
  _notification_is_excluded_command "$cmd_line" && return 0

  [[ -d "$_HERDR_IDLE_WATCH_DIR" ]] || mkdir -p "$_HERDR_IDLE_WATCH_DIR" 2>/dev/null || return 0
  local pidfile="${_HERDR_IDLE_WATCH_DIR}/${HERDR_PANE_ID//[^A-Za-z0-9._-]/_}"
  _herdr_idle_watch "$$" "$cmd_line" "$pidfile" "$threshold" "${HERDR_IDLE_WATCH_INTERVAL:-5}" >/dev/null 2>&1 &!
  _herdr_idle_watch_pid=$!
  print -r -- "$_herdr_idle_watch_pid" > "$pidfile"
}

# コマンド終了時に、自分が起動した監視を止めて⏸️を外す。pidfileの持ち主が自分でなければ
# （既に終了して後始末済み、または別シェルの監視）何もしない。持ち主確認なしでkillすると、
# 監視が先に終了した長時間コマンドの後でPIDが再利用された無関係プロセスを止めかねない。
function _herdr_idle_watch_stop() {
  [[ -n "$_herdr_idle_watch_pid" ]] || return 0
  local my_pid="$_herdr_idle_watch_pid" owner=""
  _herdr_idle_watch_pid=""
  local pidfile="${_HERDR_IDLE_WATCH_DIR}/${HERDR_PANE_ID//[^A-Za-z0-9._-]/_}"
  read -r owner < "$pidfile" 2>/dev/null
  [[ "$owner" == "$my_pid" ]] || return 0
  kill "$my_pid" 2>/dev/null
  /bin/unlink "$pidfile" 2>/dev/null
  [[ -f "${pidfile}.shown" ]] && _herdr_idle_watch_hide "$pidfile"
  return 0
}

# コマンド実行前のフック関数
function _notification_preexec() {
  # 直前コマンドの完了✅/失敗❌アイコンが残っていれば、新しいコマンドの開始時に外す
  # （✋入力待ちと違い、完了/失敗には「読んだ」相手がいないため次コマンド開始を
  # 区切りとする。tmux/Herdr両方から外す）
  if [[ -n "${_shell_status_icon_active:-}" ]]; then
    if (( ${+functions[remove_tmux_window_icon]} )); then
      remove_tmux_window_icon || true
    fi
    if (( ${+functions[remove_herdr_status_icon]} )); then
      remove_herdr_status_icon || true
    fi
    unset _shell_status_icon_active
  fi

  _cmd_start_time=$SECONDS
  _cmd_name="$1"

  # コマンド実行時の環境変数をチェックしてグローバル変数に保存
  if [[ -n "${DISABLE_NOTIFY}" ]]; then
    _DISABLE_NOTIFY_FOR_CURRENT_CMD=1
  fi

  _herdr_idle_watch_start "$1"
}

# 通知用変数を初期化する関数
function _notification_reset() {
  _cmd_start_time=0
  _cmd_name=""
}


# プロンプト表示前のフック関数
function _notification_precmd() {
  # コマンドの成功・失敗判定
  local exit_code=$?

  # 画面停止監視は通知条件（経過時間・除外）と無関係に、まず止める
  _herdr_idle_watch_stop

  # コマンドが実行されていない場合は早期リターン
  if (( _cmd_start_time <= 0 )); then
    _notification_reset
    return
  fi

  local elapsed=$(($SECONDS - _cmd_start_time))
  # 一定秒未満の場合は早期リターン
  if (( elapsed < 11 )); then
    _notification_reset
    return
  fi

  # 一時的な無効化チェック
  # グローバル変数またはコマンド実行時の環境変数をチェック
  if [[ -n "${DISABLE_NOTIFY}" ]] || [[ -n "${_DISABLE_NOTIFY_FOR_CURRENT_CMD}" ]]; then
    unset _DISABLE_NOTIFY_FOR_CURRENT_CMD
    _notification_reset
    return
  fi

  # 除外コマンドチェック
  if _notification_is_excluded_command "$_cmd_name"; then
    _notification_reset
    return
  fi

  # ユーザーによる中断の場合は早期リターン（通知しない）
  # SIGINT/Ctrl+C, SIGPIPE/git logなどの無限ストリームのページャー終了等
  if [[ $exit_code -eq $EXIT_CODE_SIGINT || $exit_code -eq $EXIT_CODE_SIGPIPE ]]; then
    _notification_reset
    return
  fi

  # 通知メッセージを設定
  local status_icon
  local status_title
  local message

  if [[ $exit_code -eq 0 ]]; then
    status_icon="✅"  # 成功
    status_title="Command Completed"
    message="${_cmd_name} (${elapsed}s)"
  else
    status_icon="❌"  # 失敗
    status_title="Command Failed"
    message="${_cmd_name} (${elapsed}s) - Exit code: ${exit_code}"
  fi

  # 通知を送信（tmux/HerdrのアイコンにもAI以外のシェル状態として反映する）
  notify --tmux-icon "${status_icon}" "${status_icon} ${status_title}" "${message}"
  _shell_status_icon_active=1

  # 最後に初期化
  _notification_reset
}

# フックを登録
add-zsh-hook preexec _notification_preexec
add-zsh-hook precmd _notification_precmd
