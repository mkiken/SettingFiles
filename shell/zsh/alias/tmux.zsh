#!/bin/zsh
# tmux aliases

alias tm='tmux'
alias tmks='tm kill-server'
alias tms='tmux-snap'

function _tmux_require_client() {
  if [[ -z "${TMUX:-}" ]]; then
    echo "tmux内で実行してください" >&2
    return 1
  fi

  return 0
}

function _tmux_quote_args() {
  local arg
  local quoted=()

  for arg in "$@"; do
    quoted+=("${(q)arg}")
  done

  print -r -- "${(j: :)quoted}"
}

function _tmux_cd_window_command() {
  local cd_command="$1"
  local rename_script="$2"

  print -r -- "if ! ${cd_command}; then exit 130; fi; ${(q)rename_script} \"\$PWD\"; exec zsh"
}

function _tmux_cd_session_command() {
  local cd_command="$1"
  local rename_script="$2"
  local origin_window="$3"

  print -r -- "if ! ${cd_command}; then current_session=\$(tmux display-message -p '#S'); tmux switch-client -t ${(q)origin_window} 2>/dev/null; tmux kill-session -t \"\$current_session\" 2>/dev/null; exit 130; fi; ${(q)rename_script} \"\$PWD\"; session_name=\$(basename -- \"\$PWD\"); session_name=\"\${session_name//:/_}\"; session_name=\"\${session_name//./_}\"; [[ -z \"\$session_name\" ]] && session_name=session; current_session=\$(tmux display-message -p '#S'); current_window=\$(tmux display-message -p '#{window_id}'); if [[ \"\$current_session\" = \"\$session_name\" ]]; then exec zsh; fi; if tmux has-session -t=\"\$session_name\" 2>/dev/null; then tmux move-window -s \"\$current_window\" -t \"\${session_name}:\"; tmux switch-client -t \"\$current_window\"; else tmux rename-session -t \"\$current_session\" \"\$session_name\"; fi; exec zsh"
}

function _tmux_path_session_command() {
  local rename_script="$1"

  print -r -- "${(q)rename_script} \"\$PWD\"; session_name=\$(basename -- \"\$PWD\"); session_name=\"\${session_name//:/_}\"; session_name=\"\${session_name//./_}\"; [[ -z \"\$session_name\" ]] && session_name=session; current_session=\$(tmux display-message -p '#S'); current_window=\$(tmux display-message -p '#{window_id}'); if [[ \"\$current_session\" = \"\$session_name\" ]]; then exec zsh; fi; if tmux has-session -t=\"\$session_name\" 2>/dev/null; then tmux move-window -s \"\$current_window\" -t \"\${session_name}:\"; tmux switch-client -t \"\$current_window\"; else tmux rename-session -t \"\$current_session\" \"\$session_name\"; fi; exec zsh"
}

function _tmux_zsh_login_command() {
  local shell_command="$1"

  print -r -- "TERM_PROGRAM=tmux zsh -lic ${(q)shell_command}"
}

function _tmux_zsh_login_command_without_rc() {
  local shell_command="$1"

  print -r -- "TERM_PROGRAM=tmux zsh -lc ${(q)shell_command}"
}

function _tmux_unique_cd_session_name() {
  local session_name

  while true; do
    session_name="__cdtmp_${$}_${RANDOM}"
    if ! tmux has-session -t="$session_name" 2>/dev/null; then
      print -r -- "$session_name"
      return 0
    fi
  done
}

function _tmux_read_path_from_stdin() {
  local line
  local target_path

  while IFS= read -r line; do
    if [[ -z "$target_path" && "$line" = /* && -d "$line" ]]; then
      target_path="$line"
    fi
  done

  if [[ -n "$target_path" ]]; then
    print -r -- "$target_path"
    return 0
  fi

  return 1
}

function _tmux_create_window_at_path() {
  local target_path="$1"
  local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles/}"
  local rename_script="${set_dir}shell/tmux/rename-window-git.sh"
  local shell_command="${(q)rename_script} \"\$PWD\"; exec zsh"
  local tmux_command=$(_tmux_zsh_login_command_without_rc "$shell_command")

  tmux new-window -c "$target_path" "$tmux_command"
}

function _tmux_create_session_at_path() {
  local target_path="$1"
  local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles/}"
  local rename_script="${set_dir}shell/tmux/rename-window-git.sh"
  local temp_session=$(_tmux_unique_cd_session_name)
  local shell_command=$(_tmux_path_session_command "$rename_script")
  local tmux_command=$(_tmux_zsh_login_command_without_rc "$shell_command")

  tmux new-session -d -s "$temp_session" -c "$target_path" "$tmux_command" &&
    tmux switch-client -t "$temp_session"
}

function create_tmux_window() {
  if ! _tmux_require_client; then
    return 1
  fi

  if [[ $# -eq 0 ]]; then
    echo "Usage: create_tmux_window <cd-command> [args...]" >&2
    return 2
  fi

  local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles/}"
  local rename_script="${set_dir}shell/tmux/rename-window-git.sh"
  local cd_command=$(_tmux_quote_args "$@")
  local shell_command=$(_tmux_cd_window_command "$cd_command" "$rename_script")
  local tmux_command=$(_tmux_zsh_login_command "$shell_command")

  tmux new-window -c "$PWD" "$tmux_command"
}

function create_tmux_session() {
  if ! _tmux_require_client; then
    return 1
  fi

  if [[ $# -eq 0 ]]; then
    echo "Usage: create_tmux_session <cd-command> [args...]" >&2
    return 2
  fi

  local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles/}"
  local rename_script="${set_dir}shell/tmux/rename-window-git.sh"
  local cd_command=$(_tmux_quote_args "$@")
  local origin_window=$(tmux display-message -p '#{window_id}')
  local temp_session=$(_tmux_unique_cd_session_name)
  local shell_command=$(_tmux_cd_session_command "$cd_command" "$rename_script" "$origin_window")
  local tmux_command=$(_tmux_zsh_login_command "$shell_command")

  tmux new-session -d -s "$temp_session" -c "$PWD" "$tmux_command" &&
    tmux switch-client -t "$temp_session"
}

function _tmux_window_from_stdin() {
  if ! _tmux_require_client; then
    return 1
  fi

  local target_path
  target_path=$(_tmux_read_path_from_stdin)
  if [[ -z "$target_path" ]]; then
    echo "入力からディレクトリを取得できませんでした" >&2
    return 1
  fi

  _tmux_create_window_at_path "$target_path"
}

function _tmux_session_from_stdin() {
  if ! _tmux_require_client; then
    return 1
  fi

  local target_path
  target_path=$(_tmux_read_path_from_stdin)
  if [[ -z "$target_path" ]]; then
    echo "入力からディレクトリを取得できませんでした" >&2
    return 1
  fi

  _tmux_create_session_at_path "$target_path"
}

# tmuxで新しくペインを作成してコマンドを実行
# 水平分割
function sp() {
  _sp "$*"
}
# 水平分割してless
function spl() {
  _sp "$* | less"
}

function _sp() {
  tmux split-window "$*"
}

# 垂直分割
function vsp() {
  _vsp "$*"
}

# 垂直分割してless
function vspl() {
  _vsp "$* | less"
}

function _vsp() {
  tmux split-window -h "$*"
}

# tmuxペインのスナップショットを撮る
function tmux-snap() {
  local filename="/tmp/tmux-snapshot-$(date '+%Y%m%d%H%M%S').txt"
  tmux capture-pane -pS - > "$filename"
  echo "スナップショットを保存しました: $filename"
}

alias tw='create_tmux_window cdi'
alias ts='create_tmux_session cdi'

alias -g W='| _tmux_window_from_stdin'
alias -g S='| _tmux_session_from_stdin'
