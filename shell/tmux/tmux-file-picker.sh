#!/usr/bin/env bash
# tmux/Herdr の popup から fzf でファイル/ディレクトリを多選択し、元ペインへ送り込むスクリプト。
# AI エージェント（claude / gemini / codex）が動いているペインを検出した場合は @path 形式で書き戻す。
# tmux/Herdr のどちらで動いているかは _mux_detect で判定し、ペイン操作は _mux_* 関数に切り出している。
# 起動例 (tmux): bind @ display-popup -E -d '#{pane_current_path}' -w 90% -h 90% '$HOME/.tmux/scripts/tmux-file-picker.sh'
# 起動例 (Herdr): [[keys.command]] key = "prefix+@" type = "popup" command = "$HOME/.tmux/scripts/tmux-file-picker.sh"
# Options: --git-root | --zoxide | --dir-only | --directories
#
# 出典:
#   記事 : https://dev.classmethod.jp/articles/shuntaka-claude-code-tmux-personal-tips/
#   実装 : https://github.com/shuntaka9576/dotfiles/blob/6def6086eb797146104aef14d63f2c2bb44dd9b1/home-manager/programs/tmux/scripts/tmux-file-picker.sh

set -euo pipefail

# tmux display-popup から起動されると login PATH を継承しないので Homebrew を明示
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

SCRIPT_PATH="${BASH_SOURCE[0]}"
if [[ $SCRIPT_PATH != /* ]]; then
  SCRIPT_PATH="$PWD/$SCRIPT_PATH"
fi

_preview_directory() {
  local target="$1"

  if command -v tree >/dev/null 2>&1; then
    tree -C "$target" | head -n 80 || true
  elif command -v eza >/dev/null 2>&1; then
    eza -T --color=always --level=2 -- "$target" | head -n 80 || true
  elif command -v exa >/dev/null 2>&1; then
    exa -T --color=always --level=2 -- "$target" | head -n 80 || true
  else
    ls -la "$target"
  fi
}

_is_image() {
  local mime
  mime=$(file --brief --dereference --mime-type -- "$1" 2>/dev/null)
  [[ $mime == image/* ]]
}

_preview_image() {
  local target="$1"
  local cols="${FZF_PREVIEW_COLUMNS:-80}" lines="${FZF_PREVIEW_LINES:-24}"

  # ANSI シンボル描画(モザイク調だが tmux popup + fzf で確実に動く)。
  # kitty graphics + Unicode プレースホルダも試したが、fzf のプレビュー経由では
  # Ghostty が合成せず断念(転送の tty 直書き・行分割・インライン化すべて不発)。
  if command -v chafa >/dev/null 2>&1; then
    # sextant/legacy シンボルで実効解像度を上げる(Ghostty はこれらを自前描画する)
    chafa -f symbols -c full -w 9 \
      --symbols "block+border+space+quad+sextant+wedge+legacy-wide-inverted" \
      --animate off -s "${cols}x$((lines - 1))" -- "$target"
    echo
  else
    file -- "$target"
  fi
}

_preview_file() {
  local target="$1"

  if _is_image "$target"; then
    _preview_image "$target"
  elif command -v bat >/dev/null 2>&1; then
    bat --style=numbers --color=always --line-range :200 -- "$target"
  elif command -v batcat >/dev/null 2>&1; then
    batcat --style=numbers --color=always --line-range :200 -- "$target"
  else
    sed -n "1,200p" "$target"
  fi
}

_preview_file_or_directory() {
  local target="$1"

  if [[ -z $target ]]; then
    return 0
  elif [[ -d $target ]]; then
    _preview_directory "$target"
  else
    _preview_file "$target"
  fi
}

_preview_grep() {
  local target="$1"

  if [[ -z $target ]]; then
    return 0
  elif [[ -n ${FZF_QUERY:-} ]]; then
    if command -v rg >/dev/null 2>&1; then
      rg --context 3 --color=always --line-number --no-heading --smart-case --max-columns 200 --max-columns-preview -- "${FZF_QUERY}" "$target" || true
    else
      printf "rg not found\n"
    fi
  else
    _preview_file_or_directory "$target"
  fi
}

_run_preview() {
  local mode="${1:-files}"
  local target="${2:-}"

  case "$mode" in
  directory)
    [[ -n $target ]] && _preview_directory "$target"
    ;;
  dynamic)
    if [[ ${FZF_PROMPT:-} == Grep* ]]; then
      _preview_grep "$target"
    else
      _preview_file_or_directory "$target"
    fi
    ;;
  files)
    _preview_file_or_directory "$target"
    ;;
  *)
    printf "unknown preview mode: %s\n" "$mode" >&2
    return 2
    ;;
  esac
}

_preview_command() {
  local mode="$1"
  local quoted_script
  printf -v quoted_script "%q" "$SCRIPT_PATH"
  printf '%s --preview %s {}' "$quoted_script" "$mode"
}

_ai_at_path() {
  local path="$1"
  printf '@%s' "$path"
}

if [[ ${1:-} == "--preview" ]]; then
  shift
  _run_preview "$@"
  exit $?
fi

# pgrep -P は直接の子のみ対象。tmux 経由では pane_pid → login-shell → ai-cli と
# 2段階になるため、ps で子孫を最大3世代まで再帰検索する
_has_ai_descendant() {
    local parent="$1"
    local depth="${2:-0}"
    [[ $depth -ge 3 ]] && return 1

    while IFS= read -r cpid; do
        [[ -z $cpid ]] && continue
        local cmd
        cmd=$(ps -p "$cpid" -o command= 2>/dev/null | head -1)
        if [[ $cmd =~ (claude|gemini|codex) ]]; then
            return 0
        fi
        _has_ai_descendant "$cpid" "$((depth + 1))" && return 0
    done < <(ps -eo ppid=,pid= 2>/dev/null | awk -v p="$parent" '$1==p {print $2}')

    return 1
}

# --- Multiplexer abstraction (tmux / Herdr) ---
# tmux を優先（tmux セッション内で HERDR_ENV が漏れ継承していても既存の tmux フローを変えないため）。
_mux_detect() {
  if [[ -n ${TMUX-} ]]; then
    echo tmux
  elif [[ ${HERDR_ENV-} == 1 ]]; then
    echo herdr
  else
    echo none
  fi
}

# 送信先ペイン ID を返す。
_mux_pane_id() {
  local mux="$1"
  case "$mux" in
  tmux)
    tmux display-message -p '#{pane_id}'
    ;;
  herdr)
    # popup 内では HERDR_PANE_ID は注入されず、元ペインは HERDR_ACTIVE_PANE_ID が指す。
    echo "${HERDR_ACTIVE_PANE_ID:?Error: HERDR_ACTIVE_PANE_ID is not set (not running inside a Herdr popup?)}"
    ;;
  esac
}

# 検索起点ディレクトリを返す。
_mux_pane_dir() {
  local mux="$1" pane_id="$2"
  case "$mux" in
  tmux)
    tmux display-message -p '#{pane_current_path}'
    ;;
  herdr)
    # Herdr は popup に元ペインの cwd を HERDR_ACTIVE_PANE_CWD として直接渡すため CLI 呼び出しは不要。
    echo "${HERDR_ACTIVE_PANE_CWD:?Error: HERDR_ACTIVE_PANE_CWD is not set}"
    ;;
  esac
}

# 指定ペインで AI エージェント（claude/gemini/codex）が動いていれば真を返す。
_mux_is_ai_pane() {
  local mux="$1" pane_id="$2"
  case "$mux" in
  tmux)
    # tmux では pane_pid 起点の ps 子孫探索で判定する（引数の pane_id は使わない）。
    local pane_pid
    pane_pid=$(tmux display-message -p '#{pane_pid}')
    _has_ai_descendant "$pane_pid"
    ;;
  herdr)
    local herdr_bin agent
    herdr_bin="${HERDR_BIN_PATH:-herdr}"
    agent=$("$herdr_bin" pane get "$pane_id" 2>/dev/null | jq -r '.result.pane.agent // empty' 2>/dev/null || true)
    [[ $agent =~ ^(claude|gemini|codex)$ ]]
    ;;
  esac
}

# 指定ペインへテキストを送り込む（改行なし挿入）。
_mux_send_text() {
  local mux="$1" pane_id="$2" text="$3"
  case "$mux" in
  tmux)
    tmux send-keys -t "$pane_id" "$text"
    ;;
  herdr)
    local herdr_bin
    herdr_bin="${HERDR_BIN_PATH:-herdr}"
    # `herdr pane send-text` は <pane_id> <text> の2引数固定で `--` セパレータを解釈しない
    # （挟むと "--" がリテラルな text 先頭に混入する）。素直に2引数で渡す。
    "$herdr_bin" pane send-text "$pane_id" "$text"
    ;;
  esac
}

_select_zoxide_dir() {
  if ! command -v zoxide >/dev/null 2>&1; then
    echo "Error: Required command 'zoxide' not found. Please install it." >&2
    exit 1
  fi

  local zoxide_preview_cmd
  zoxide_preview_cmd=$(_preview_command directory)

  # Use fzf to select directories from zoxide's list.
  # The '|| true' prevents the script from exiting if the user cancels fzf.
  local dirs
  dirs=$(zoxide query -l | SHELL=/bin/bash fzf --multi --cycle --reverse --preview "$zoxide_preview_cmd" || true)
  echo "$dirs"
}

main() {
  local mux
  mux=$(_mux_detect)
  if [[ $mux == none ]]; then
    echo "Error: This script must be run inside a tmux session or a Herdr popup." >&2
    exit 1
  fi

  local pane_id
  local pane_dir
  pane_id=$(_mux_pane_id "$mux")
  pane_dir=$(_mux_pane_dir "$mux" "$pane_id")

  # --- Argument Parsing ---
  local use_git_root=false
  local use_zoxide=false
  local dir_only=false
  local select_directories=false
  local path_arg=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
    --git-root | -g)
      use_git_root=true
      shift
      ;;
    --zoxide)
      use_zoxide=true
      shift
      ;;
    --dir-only)
      dir_only=true
      shift
      ;;
    --directories | -d)
      select_directories=true
      shift
      ;;
    -*)
      echo "Error: Unknown option '$1'" >&2
      exit 1
      ;;
    *)
      if [[ -n $path_arg ]]; then
        echo "Error: Only one path argument is allowed." >&2
        exit 1
      fi
      path_arg="$1"
      shift
      ;;
    esac
  done

  # Check for conflicting arguments
  if $use_zoxide && [[ -n $path_arg ]]; then
    echo "Error: The --zoxide flag cannot be used with a path argument." >&2
    exit 1
  fi

  if $dir_only && ! $use_zoxide; then
    echo "Error: The --dir-only flag can only be used with --zoxide." >&2
    exit 1
  fi

  local search_dirs=()

  if $use_zoxide; then
    local zoxide_output
    zoxide_output=$(_select_zoxide_dir)
    # Exit gracefully if no directory was selected from fzf
    if [[ -z $zoxide_output ]]; then
      exit 0
    fi
    # Split multiline output into array
    while IFS= read -r line; do
      [[ -n $line ]] && search_dirs+=("$line")
    done <<<"$zoxide_output"
  else
    local search_dir="${path_arg:-$pane_dir}"

    # Convert to absolute path if relative
    if [[ $search_dir != /* ]]; then
      search_dir="$pane_dir/$search_dir"
    fi

    # Use realpath to resolve ".." and "." components and get a canonical path
    local realpath_cmd="realpath"
    [[ $OSTYPE == "darwin"* ]] && realpath_cmd="grealpath"

    if command -v "$realpath_cmd" >/dev/null 2>&1; then
      search_dir=$("$realpath_cmd" -m "$search_dir")
    fi
    search_dirs=("$search_dir")
  fi

  # Verify all directories exist
  for dir in "${search_dirs[@]}"; do
    if [[ ! -d $dir ]]; then
      echo "Error: Directory '$dir' does not exist." >&2
      exit 1
    fi
  done

  # --- Mode Detection ---
  local at_prefix_mode=false
  if _mux_is_ai_pane "$mux" "$pane_id"; then
    at_prefix_mode=true
  fi

  local git_root
  git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
  if $use_git_root && [[ -z $git_root ]]; then
    echo "Error: --git-root flag used, but not inside a git repository." >&2
    exit 1
  fi

  # If --dir-only is set, just output the directory paths and exit
  if $dir_only; then
    local output_str=""
    if $at_prefix_mode; then
      for dir in "${search_dirs[@]}"; do
        output_str+="$(_ai_at_path "$dir") "
      done
    else
      local escaped_paths=()
      for dir in "${search_dirs[@]}"; do
        local escaped
        printf -v escaped "%q" "$dir"
        escaped_paths+=("$escaped")
      done
      output_str=$(printf "%s " "${escaped_paths[@]}")
    fi
    _mux_send_text "$mux" "$pane_id" "$output_str"
    exit 0
  fi

  # --- Command Detection ---
  local fd_cmd
  if command -v fd >/dev/null 2>&1; then
    fd_cmd="fd"
  elif command -v fdfind >/dev/null 2>&1; then
    fd_cmd="fdfind"
  else
    echo "Error: Required command 'fd' or 'fdfind' not found. Please install it." >&2
    exit 1
  fi

  # --- File/Directory Selection ---
  local fd_flags
  local preview_cmd
  local grep_preview_cmd
  local grep_reload_cmd
  local fd_flags_array=()
  local grep_toggle_flags=()

  if $select_directories; then
    # Directory selection mode
    fd_flags="${TMUX_FILE_PICKER_FD_FLAGS:--H --follow --type d --exclude .git}"
    preview_cmd=$(_preview_command directory)
  else
    # File and directory selection mode (default)
    fd_flags="${TMUX_FILE_PICKER_FD_FLAGS:--H --follow --type f --type d --exclude .git --exclude .DS_Store}"
    preview_cmd=$(_preview_command files)

    # Grep mode toggle (C-s to switch between file search and content grep)
    # $FZF_PROMPT is available in preview commands since fzf 0.50+
    if command -v rg >/dev/null 2>&1; then
      grep_reload_cmd="if [ -n \"\$FZF_QUERY\" ]; then rg --files-with-matches --hidden --glob '!.git' --color=never -- \"\$FZF_QUERY\" 2>/dev/null || true; else printf \"\"; fi"
    else
      grep_reload_cmd='printf ""'
    fi
    grep_preview_cmd=$(_preview_command dynamic)

    local desktop_dir="${HOME}/Desktop"
    local desktop_reload_cmd='printf ""'
    if [[ -d $desktop_dir ]]; then
      local desktop_dir_arg
      printf -v desktop_dir_arg "%q" "$desktop_dir"
      desktop_reload_cmd="$fd_cmd --absolute-path --max-depth 1 $fd_flags . $desktop_dir_arg"
    fi

    local downloads_dir="${HOME}/Downloads"
    local downloads_reload_cmd='printf ""'
    if [[ -d $downloads_dir ]]; then
      local downloads_dir_arg
      printf -v downloads_dir_arg "%q" "$downloads_dir"
      downloads_reload_cmd="$fd_cmd --absolute-path --max-depth 1 $fd_flags . $downloads_dir_arg"
    fi

    grep_toggle_flags=(
      --prompt 'Files> '
      --header 'C-s: grep/files | C-d: desktop | C-l: downloads'
      --preview "$grep_preview_cmd"
      --bind 'start:unbind(change)'
      --bind "change:reload:$grep_reload_cmd"
      --bind "ctrl-s:transform:[[ \$FZF_PROMPT == \"Files> \" ]] && echo \"change-prompt(Grep> )+disable-search+clear-query+reload(: || true)+rebind(change)\" || echo \"change-prompt(Files> )+enable-search+clear-query+unbind(change)+reload($fd_cmd $fd_flags)\""
      --bind "ctrl-d:transform:[[ \$FZF_PROMPT == \"Desktop> \" ]] && echo \"change-prompt(Files> )+enable-search+clear-query+unbind(change)+reload($fd_cmd $fd_flags)\" || echo \"change-prompt(Desktop> )+enable-search+clear-query+unbind(change)+reload($desktop_reload_cmd)\""
      --bind "ctrl-l:transform:[[ \$FZF_PROMPT == \"Downloads> \" ]] && echo \"change-prompt(Files> )+enable-search+clear-query+unbind(change)+reload($fd_cmd $fd_flags)\" || echo \"change-prompt(Downloads> )+enable-search+clear-query+unbind(change)+reload($downloads_reload_cmd)\""
    )
  fi

  read -r -a fd_flags_array <<<"$fd_flags"

  local selected_files_str
  # --reverse を外しデフォルトレイアウト(プロンプト下端・最良候補が直上)にする。
  # Neovim 側 Telescope ピッカーの sorting_strategy デフォルト "descending"(最良が下)
  # とソート位置を揃えるための意図的な選択。--zoxide 側の fzf 呼び出しは対応する
  # Neovim ピッカーが無いため --reverse を維持しており、この2箇所とは非対称。
  if [[ ${#search_dirs[@]} -eq 1 ]]; then
    # Single directory: cd into it for cleaner relative paths in fzf
    selected_files_str=$(cd "${search_dirs[0]}" && "$fd_cmd" "${fd_flags_array[@]}" | SHELL=/bin/bash fzf --multi --cycle --freeze-right=1 --bind 'tab:toggle' --preview "$preview_cmd" "${grep_toggle_flags[@]}" || true)
  else
    # Multiple directories: pass them as arguments to fd (returns absolute paths)
    selected_files_str=$("$fd_cmd" "${fd_flags_array[@]}" "${search_dirs[@]}" | SHELL=/bin/bash fzf --multi --cycle --freeze-right=1 --bind 'tab:toggle' --preview "$preview_cmd" "${grep_toggle_flags[@]}" || true)
  fi

  if [[ -z $selected_files_str ]]; then
    if $use_zoxide; then
      # If zoxide was used but file selection cancelled, continue to output the directories
      :
    else
      exit 0
    fi
  fi

  # --- Path Processing ---
  selected_files=()
  while IFS= read -r line; do
    if [[ -n $line ]]; then
      selected_files+=("$line")
    fi
  done <<<"$selected_files_str"

  # --- Path Relativization ---
  local relative_paths=()

  # When using zoxide or explicit path arg, return absolute paths
  if $use_zoxide || [[ -n $path_arg ]]; then
    if [[ ${#selected_files[@]} -eq 0 ]]; then
      # Fallback: output the directories themselves if no files were selected
      relative_paths=("${search_dirs[@]}")
    elif [[ ${#search_dirs[@]} -eq 1 ]]; then
      # Single directory mode: fd returned relative paths, prepend the directory
      relative_paths=("${selected_files[@]/#/${search_dirs[0]}\/}")
    else
      # Multiple directories mode: fd returned absolute paths, use as-is
      relative_paths=("${selected_files[@]}")
    fi
  elif [[ ${#selected_files[@]} -gt 0 && ${selected_files[0]} == /* ]]; then
    # Desktop/Downloads modes return absolute paths so AI CLIs can read files outside the repository.
    relative_paths=("${selected_files[@]}")
  else
    # Standard path relativization logic (non-zoxide always has single directory)
    local search_dir="${search_dirs[0]}"
    local base_dir_for_relativization=""

    if $use_git_root; then
      base_dir_for_relativization="$git_root"
    fi

    if [[ -n $base_dir_for_relativization ]]; then
      # We need to calculate relative paths against a specific base directory
      local realpath_cmd="realpath"
      [[ $OSTYPE == "darwin"* ]] && realpath_cmd="grealpath"

      # Prepend search directory to each filename to create full paths
      local full_paths=("${selected_files[@]/#/$search_dir\/}")

      while IFS= read -r line; do
        if [[ -n $line ]]; then
          relative_paths+=("$line")
        fi
      done < <("$realpath_cmd" --relative-to="$base_dir_for_relativization" "${full_paths[@]}")
    else
      # Paths are already relative to the correct directory (the pane_dir)
      relative_paths=("${selected_files[@]}")
    fi
  fi

  # --- Output Formatting ---
  local files_oneline
  if $at_prefix_mode; then
    # Prefix each file with '@' and join with spaces
    files_oneline=""
    for path in "${relative_paths[@]}"; do
      files_oneline+="$(_ai_at_path "$path") "
    done
  else
    # Shell-escape each file path and join with spaces
    local escaped_paths=()
    for path in "${relative_paths[@]}"; do
      printf -v escaped_path "%q" "$path"
      escaped_paths+=("$escaped_path")
    done
    files_oneline=$(printf "%s " "${escaped_paths[@]}")
  fi

  # --- Send to the multiplexer ---
  _mux_send_text "$mux" "$pane_id" "$files_oneline"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
