function notify() {
  local title="$1"
  local message="$2"
  local sound="${3:-default}"
  local group="$4"

  # terminal-notifierがない場合は早期リターン
  if ! command -v terminal-notifier >/dev/null 2>&1; then
    echo "terminal-notifier not found. Please install.\n"
    return 1
  fi

  # Bundle ID決定ロジック
  # 優先度: $__CFBundleIdentifier > $TERM_PROGRAM > $TERMINAL_EMULATOR (JetBrains) > デフォルト(Ghostty)
  # osascript による frontmost アプリ検出は非決定的なため使わない
  local bundle_id="${__CFBundleIdentifier}"

  # TERM_PROGRAM によるマッピング（ほとんどのターミナルがセットする変数）
  if [[ -z "$bundle_id" ]]; then
    case "${TERM_PROGRAM}" in
      ghostty)        bundle_id="com.mitchellh.ghostty" ;;
      vscode)         bundle_id="com.microsoft.VSCode" ;;
      iTerm.app)      bundle_id="com.googlecode.iterm2" ;;
      Apple_Terminal) bundle_id="com.apple.Terminal" ;;
    esac
  fi

  # JetBrains IDE（TERMINAL_EMULATOR=JetBrains-JediTerm）
  if [[ -z "$bundle_id" && "${TERMINAL_EMULATOR}" == "JetBrains-JediTerm" ]]; then
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