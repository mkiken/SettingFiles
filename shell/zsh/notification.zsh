#!/usr/local/bin/zsh

# 長時間実行コマンドの通知設定
# コマンド実行開始時間を記録
_cmd_start_time=0
_cmd_name=""

# preexec: コマンド実行前に呼ばれる
function preexec() {
  _cmd_start_time=$SECONDS
  _cmd_name="$1"
}

# precmd: コマンド実行後、プロンプト表示前に呼ばれる
function precmd() {
  if (( _cmd_start_time > 0 )); then
    local elapsed=$(($SECONDS - _cmd_start_time))
    if (( elapsed >= 5 )); then
      # terminal-notifierがインストールされている場合のみ通知
      if command -v terminal-notifier >/dev/null 2>&1; then
        terminal-notifier -title "Command Complete" \
          -message "${_cmd_name} finished (${elapsed}s)" \
          -sound default
      fi
    fi
  fi
  _cmd_start_time=0
  _cmd_name=""
}