#!/bin/zsh

# 通知を無効化するコマンドのリスト
export NOTIFY_COMMAND_EXCLUDE=(
  claude
  less
  nvim
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

# コマンド実行前のフック関数
function _notification_preexec() {
  _cmd_start_time=$SECONDS
  _cmd_name="$1"

  # コマンド実行時の環境変数をチェックしてグローバル変数に保存
  if [[ -n "${DISABLE_NOTIFY}" ]]; then
    _DISABLE_NOTIFY_FOR_CURRENT_CMD=1
  fi
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

  # 一時的な無効化チェック
  # グローバル変数またはコマンド実行時の環境変数をチェック
  if [[ -n "${DISABLE_NOTIFY}" ]] || [[ -n "${_DISABLE_NOTIFY_FOR_CURRENT_CMD}" ]]; then
    unset _DISABLE_NOTIFY_FOR_CURRENT_CMD
    _notification_reset
    return
  fi

  # 除外コマンドチェック
  if [[ -n "${NOTIFY_COMMAND_EXCLUDE}" ]]; then
    # コマンド名を抽出（最初の単語、パス削除）
    local cmd_name="${_cmd_name%% *}"
    cmd_name="${cmd_name##*/}"

    # 配列としてチェック
    if (( ${NOTIFY_COMMAND_EXCLUDE[(Ie)$cmd_name]} )); then
      _notification_reset
      return
    fi
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

  # 通知を送信
  notify "${status_icon} ${status_title}" "${message}"

  # 最後に初期化
  _notification_reset
}

# フックを登録
add-zsh-hook preexec _notification_preexec
add-zsh-hook precmd _notification_precmd