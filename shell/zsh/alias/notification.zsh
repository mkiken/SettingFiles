function notify() {
  # terminal-notifierがない場合は早期リターン
  if ! command -v terminal-notifier >/dev/null 2>&1; then
    echo "terminal-notifier not found. Please install.\n"
    return 1
  fi
  local title="$1"
  local message="$2"
  local sound="${3:-default}"

  terminal-notifier -title "$title" \
    -message "$message" \
    -sound "$sound" \
    -execute "open -a Ghostty" \
    -ignoreDnD
}

# 通知を無効化してコマンドを実行する汎用関数
no_notify() {
    export _DISABLE_NOTIFY_FOR_CURRENT_CMD=1 && "$@"
}