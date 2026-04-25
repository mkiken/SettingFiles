function notify() {
  local title="$1"
  local message="$2"
  local sound="${3:-default}"
  local group="$4"
  local time_override="${5:-}"

  # terminal-notifierがない場合は早期リターン
  if ! command -v terminal-notifier >/dev/null 2>&1; then
    echo "terminal-notifier not found. Please install.\n"
    return 1
  fi

  # タイトルに tmuxウィンドウ番号と時刻を自動付与（NOTIFY_NO_DECORATE=1 で抑制可）
  if [[ -z "${NOTIFY_NO_DECORATE}" ]]; then
    if ! command -v get_tmux_window_label >/dev/null 2>&1; then
      local _twi="${HOME}/Desktop/repository/SettingFiles/shell/tmux/tmux_window_info.sh"
      [[ -f "$_twi" ]] && source "$_twi"
    fi
    local tmux_label=""
    if command -v get_tmux_window_label >/dev/null 2>&1; then
      tmux_label=$(get_tmux_window_label)
    fi
    local display_time="${time_override:-$(date "+%H:%M:%S")}"
    title="${title}${tmux_label} 🕰️${display_time}"
  fi

  # Bundle ID決定ロジック
  # tmux内ではシェルの環境変数がtmuxサーバー起動元の値を保持しており不正確
  # .tmux.conf の update-environment によりアタッチ時に更新されるセッション環境を優先して使う
  # osascript による frontmost アプリ検出は非決定的なため使わない
  local bundle_id=""
  local term_program=""
  local terminal_emulator=""

  if [[ -n "$TMUX" ]]; then
    local val
    val=$(tmux show-environment __CFBundleIdentifier 2>/dev/null)
    [[ "$val" == __CFBundleIdentifier=* ]] && bundle_id="${val#*=}"

    val=$(tmux show-environment TERM_PROGRAM 2>/dev/null)
    [[ "$val" == TERM_PROGRAM=* ]] && term_program="${val#*=}"

    val=$(tmux show-environment TERMINAL_EMULATOR 2>/dev/null)
    [[ "$val" == TERMINAL_EMULATOR=* ]] && terminal_emulator="${val#*=}"
  else
    bundle_id="${__CFBundleIdentifier}"
    term_program="${TERM_PROGRAM}"
    terminal_emulator="${TERMINAL_EMULATOR}"
  fi

  # TERM_PROGRAMによるマッピング（ほとんどのターミナルがセットする変数）
  if [[ -z "$bundle_id" ]]; then
    case "$term_program" in
      ghostty)        bundle_id="com.mitchellh.ghostty" ;;
      vscode)         bundle_id="com.microsoft.VSCode" ;;
      iTerm.app)      bundle_id="com.googlecode.iterm2" ;;
      Apple_Terminal) bundle_id="com.apple.Terminal" ;;
    esac
  fi

  # JetBrains IDE（TERMINAL_EMULATOR=JetBrains-JediTerm）
  if [[ -z "$bundle_id" && "$terminal_emulator" == "JetBrains-JediTerm" ]]; then
    bundle_id="com.jetbrains.goland"
  fi

  # 最終デフォルト値
  if [[ -z "$bundle_id" ]]; then
    bundle_id="com.mitchellh.ghostty"
  fi

  # デバッグログ
  # echo "[$(date '+%Y-%m-%d %H:%M:%S')] notify called with bundle_id='${bundle_id}', __CFBundleIdentifier='${__CFBundleIdentifier}'" >> /tmp/notification-debug.log

  # アイコンファイルが存在する場合は使用する
  # アイコンは ~/.config/notify-icons/<bundle_id>.png に置く
  local icon_path="${HOME}/.config/notify-icons/${bundle_id}.png"
  local icon_option=()
  if [[ -f "$icon_path" ]]; then
    icon_option=(-contentImage "${icon_path}")
  fi

  local group_option=()
  if [[ -n "$group" ]]; then
    group_option=(-group "$group")
  fi

  terminal-notifier -title "$title" \
    -message "$message" \
    -sound "$sound" \
    -activate "$bundle_id" \
    "${icon_option[@]}" \
    "${group_option[@]}" \
    -ignoreDnD
}

# 通知を無効化してコマンドを実行する汎用関数
no_notify() {
    export _DISABLE_NOTIFY_FOR_CURRENT_CMD=1 && "$@"
}