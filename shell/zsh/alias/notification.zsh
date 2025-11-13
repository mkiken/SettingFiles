function notify() {
  local title="$1"
  local message="$2"
  local sound="${3:-default}"
  local ide_hint="${4:-}"  # 第4引数: IDEのヒント (オプショナル)

  # terminal-notifierがない場合は早期リターン
  if ! command -v terminal-notifier >/dev/null 2>&1; then
    echo "terminal-notifier not found. Please install.\n"
    return 1
  fi

  # IDE/ターミナル判定ロジック
  # デフォルトはGhosttyのBundle ID
  local bundle_id="com.mitchellh.ghostty"

  # 第4引数でIDEが明示的に指定されている場合はそれを使用
  if [[ -n "${ide_hint}" ]]; then
    case "${ide_hint}" in
      vscode)
        bundle_id="com.microsoft.VSCode"
        ;;
      ghostty)
        bundle_id="com.mitchellh.ghostty"
        ;;
    esac
  fi

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