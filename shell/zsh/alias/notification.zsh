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
  # 優先度: 環境変数 $__CFBundleIdentifier > アクティブアプリ検出 > デフォルト値(Ghostty)
  local bundle_id="${__CFBundleIdentifier}"

  # 環境変数が未設定の場合、アクティブなアプリのBundle IDを自動検出
  if [[ -z "$bundle_id" ]]; then
    bundle_id=$(osascript -e 'tell application "System Events" to get bundle identifier of first application process whose frontmost is true' 2>/dev/null)
  fi

  # それでも取得できない場合はデフォルト値を使用
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