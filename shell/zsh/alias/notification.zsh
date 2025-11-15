function notify() {
  local title="$1"
  local message="$2"
  local sound="${3:-default}"

  # terminal-notifierがない場合は早期リターン
  if ! command -v terminal-notifier >/dev/null 2>&1; then
    echo "terminal-notifier not found. Please install.\n"
    return 1
  fi

  # Bundle ID決定ロジック
  # 優先度: 環境変数 $__CFBundleIdentifier > デフォルト値(Ghostty)
  local bundle_id="${__CFBundleIdentifier:-com.mitchellh.ghostty}"

  terminal-notifier -title "$title" \
    -message "$message" \
    -sound "$sound" \
    -activate "$bundle_id" \
    -ignoreDnD
}

# 通知を無効化してコマンドを実行する汎用関数
no_notify() {
    export _DISABLE_NOTIFY_FOR_CURRENT_CMD=1 && "$@"
}