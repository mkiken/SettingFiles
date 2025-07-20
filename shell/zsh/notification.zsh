#!/usr/local/bin/zsh

# 長時間実行コマンドの通知設定
# コマンド実行開始時間を記録
_cmd_start_time=0
_cmd_name=""

# コマンド実行前のフック関数
function _notification_preexec() {
  _cmd_start_time=$SECONDS
  _cmd_name="$1"
}

# プロンプト表示前のフック関数
function _notification_precmd() {
  # コマンドの成功・失敗判定
  local exit_code=$?
  local status_icon
  local status_title
  if [[ $exit_code -eq 0 ]]; then
    status_icon="✅"  # 成功
    status_title="Command Completed"
  else
    status_icon="❌"  # 失敗
    status_title="Command Failed"
  fi

  if (( _cmd_start_time > 0 )); then
    local elapsed=$(($SECONDS - _cmd_start_time))
    if (( elapsed >= 5 )); then
      # terminal-notifierがインストールされている場合のみ通知
      if command -v terminal-notifier >/dev/null 2>&1; then
        terminal-notifier -title "${status_icon} ${status_title}" \
          -message "${_cmd_name} finished (${elapsed}s) - Exit code: ${exit_code}" \
          -sound default
      fi
    fi
  fi
  _cmd_start_time=0
  _cmd_name=""
}

# フックを登録
add-zsh-hook preexec _notification_preexec
add-zsh-hook precmd _notification_precmd