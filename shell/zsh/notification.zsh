#!/bin/zsh

# 長時間実行コマンドの通知設定
# コマンド実行開始時間を記録
_cmd_start_time=0
_cmd_name=""

# コマンド実行前のフック関数
function _notification_preexec() {
  _cmd_start_time=$SECONDS
  _cmd_name="$1"
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

  # コマンドが実行されていない場合は早期リターン
  if (( _cmd_start_time <= 0 )); then
    _notification_reset
    return
  fi

  local elapsed=$(($SECONDS - _cmd_start_time))
  # 5秒未満の場合は早期リターン
  if (( elapsed < 5 )); then
    _notification_reset
    return
  fi

  # ユーザーによる中断の場合は早期リターン（通知しない）
  # SIGINT/Ctrl+C, SIGPIPE/git logなどの無限ストリームのページャー終了等
  if [[ $exit_code -eq $EXIT_CODE_SIGINT || $exit_code -eq $EXIT_CODE_SIGPIPE ]]; then
    _notification_reset
    return
  fi

  # terminal-notifierがない場合は早期リターン
  if ! command -v terminal-notifier >/dev/null 2>&1; then
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

  # 通知を送信
  terminal-notifier -title "${status_icon} ${status_title}" \
    -message "${message}" \
    -sound default

  # 最後に初期化
  _notification_reset
}

# フックを登録
add-zsh-hook preexec _notification_preexec
add-zsh-hook precmd _notification_precmd