#!/bin/zsh
# Utility functions shared between setup scripts and interactive shell

# tmuxウィンドウ名操作・通知タイトル生成ヘルパー
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_window_name.sh" 2>/dev/null
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_notification_title.sh" 2>/dev/null

function make_symlink () {
  local src="$1"
  local dst="$2"
  local link_path="$dst"

  if [[ -z "$src" || -z "$dst" ]]; then
    echo "Usage: make_symlink <source> <destination>" >&2
    return 1
  fi

  if [[ ! -L "$dst" && -d "$dst" ]]; then
    link_path="${dst%/}/$(basename "$src")"
  fi

  # リンク先のディレクトリを取得
  local target_dir="$(dirname "$link_path")"

  # ディレクトリが存在しない場合は作成
  if [[ ! -d "$target_dir" ]]; then
    echo "mkdir -p $target_dir"
    mkdir -p "$target_dir"
  fi

  # 既にシンボリックリンクが存在する場合の処理
  if [[ -L "$link_path" ]]; then
    local existing_target="$(readlink "$link_path")"
    if [[ "$existing_target" == "$src" ]]; then
      echo "✓ Already linked: $link_path -> $src"
      return 0
    fi
    # 異なるリンク先のシンボリックリンクは削除して再作成
    echo "rm $link_path (was -> $existing_target)"
    /bin/rm "$link_path"
  elif [[ -e "$link_path" ]]; then
    if ! (( ${+functions[notify]} )); then
      source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh" 2>/dev/null
    fi

    local review_signature=""
    local last_reviewed_at=""
    local repeated_action=""

    review_signature=$(_diff_review_symlink_signature "$src" "$link_path" 2>/dev/null || true)
    if [[ -n "$review_signature" ]]; then
      last_reviewed_at=$(_diff_review_last_reviewed_at "$review_signature" 2>/dev/null || true)
      if [[ -n "$last_reviewed_at" ]]; then
        if _diff_review_reprompt_enabled; then
          repeated_action=$(_diff_review_prompt_repeated_symlink "$review_signature" "$last_reviewed_at" "$src" "$link_path")
        else
          repeated_action="skip"
        fi
        case "$repeated_action" in
          skip)
            echo "Skipped: $link_path (前回確認時と同じ差分です: $last_reviewed_at)"
            return 0
            ;;
          view)
            _diff_review_show_symlink_change "$src" "$link_path"
            ;;
          overwrite)
            ;;
        esac
      fi
    fi

    if [[ -z "$last_reviewed_at" ]]; then
      _diff_review_show_symlink_change "$src" "$link_path"
    fi

    if [[ "$repeated_action" == "overwrite" ]] || {
      [[ -n "$review_signature" && -z "$last_reviewed_at" ]] && _diff_review_record "$review_signature"
      confirm "シンボリックリンクではない既存パスがあります: $link_path。$src へのsymlinkで上書きしますか？" --default-no --no-cancel-msg
    }; then
      if [[ -d "$link_path" ]]; then
        echo "rm -rf $link_path"
        /bin/rm -rf "$link_path"
      else
        echo "rm -f $link_path"
        /bin/rm -f "$link_path"
      fi
    else
      echo "Skipped: $link_path"
      return 0
    fi
  fi

  echo "ln -si $src $dst"
  ln -si "$src" "$dst"
}

function ensure_settingfiles_zsh_loader() {
  local zshrc="${1:-$HOME/.zshrc}"
  local managed_rc="${2:-${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/managed.zsh}"
  local start_marker="# >>> SettingFiles managed zsh >>>"
  local end_marker="# <<< SettingFiles managed zsh <<<"
  local existing_content=""
  local target_dir

  target_dir="$(dirname "$zshrc")"
  if [[ ! -d "$target_dir" ]]; then
    echo "mkdir -p $target_dir"
    mkdir -p "$target_dir"
  fi

  if [[ -L "$zshrc" ]]; then
    echo "rm $zshrc (was -> $(readlink "$zshrc"))"
    /bin/rm "$zshrc"
  elif [[ -e "$zshrc" ]]; then
    existing_content="$(
      awk -v start="$start_marker" -v end="$end_marker" '
        $0 == start { skipping = 1; next }
        $0 == end { skipping = 0; next }
        !skipping { print }
      ' "$zshrc"
    )"
  fi

  {
    print -r -- "$start_marker"
    print -r -- "if [[ -r \"$managed_rc\" ]]; then"
    print -r -- "  source \"$managed_rc\""
    print -r -- "fi"
    print -r -- "$end_marker"
    if [[ -n "$existing_content" ]]; then
      print
      print -r -- "$existing_content"
    fi
  } >| "$zshrc"
}

function homebrew_prefix() {
  if [[ -n "${BREW_PREFIX:-}" ]]; then
    print -r -- "$BREW_PREFIX"
  elif command -v brew >/dev/null 2>&1; then
    brew --prefix
  elif [[ -x /opt/homebrew/bin/brew ]]; then
    /opt/homebrew/bin/brew --prefix
  elif [[ -x /usr/local/bin/brew ]]; then
    /usr/local/bin/brew --prefix
  else
    print -r -- "/opt/homebrew"
  fi
}

function homebrew_npm() {
  local homebrew_prefix_path
  homebrew_prefix_path="$(homebrew_prefix)"
  local npm_bin="${homebrew_prefix_path}/bin/npm"

  if [[ ! -x "$npm_bin" ]]; then
    echo "Homebrew npm not found: $npm_bin" >&2
    return 1
  fi

  PATH="${homebrew_prefix_path}/bin:$PATH" "$npm_bin" "$@"
}

# Run a Homebrew-installed CLI with Homebrew bin first on PATH.
# Project-local Node managers (nvm/mise) can pin an old Node; prepending PATH on
# the same command line as the execution leaves precmd hooks no chance to
# rewrite it, so the CLI always runs on Homebrew's node.
function homebrew_run() {
  local homebrew_prefix_path
  homebrew_prefix_path="$(homebrew_prefix)"
  local cmd_bin="${homebrew_prefix_path}/bin/$1"

  if [[ ! -x "$cmd_bin" ]]; then
    echo "homebrew_run: Homebrew command not found: $cmd_bin" >&2
    return 1
  fi

  shift
  PATH="${homebrew_prefix_path}/bin:$PATH" "$cmd_bin" "$@"
}

# Copy file only if destination does not exist (with warning if it exists)
function copy_if_not_exists() {
    local src="$1"
    local dst="$2"

    if [[ -z "$src" || -z "$dst" ]]; then
        echo "Usage: copy_if_not_exists <source> <destination>"
        return 1
    fi

    # コピー先のディレクトリを取得
    local target_dir="$(dirname "$dst")"

    # ディレクトリが存在しない場合は作成
    if [[ ! -d "$target_dir" ]]; then
        echo "mkdir -p $target_dir"
        mkdir -p "$target_dir"
    fi

    local cmd="cp -n \"$src\" \"$dst\""
    echo "$cmd"
    if eval "$cmd"; then
        return 0
    else
        echo "\n⚠️  Warning: $dst already exists. Please remove it first.\n"
        return 1
    fi
}

# Show file differences with color if available
function show_file_diff() {
    local file1="$1"
    local file2="$2"
    local label1="${3:-$file1}"
    local label2="${4:-$file2}"

    echo "Source: $label1"
    if [[ "$label1" != "$file1" ]]; then
        echo "Source internal file: $file1"
    fi
    echo "Destination: $label2"
    if [[ "$label2" != "$file2" ]]; then
        echo "Destination internal file: $file2"
    fi
    echo "Diff direction: $label2 -> $label1"
    echo ""

    # Use difft if available, otherwise use regular diff
    if command -v difft &> /dev/null; then
        difft "$file2" "$file1" || true
    else
        diff -u "$file2" "$file1" || true
    fi
}

# Show JSON file differences with sorted (semantic) and original (raw) diffs
function show_json_diff() {
    local file1="$1"
    local file2="$2"
    local label1="${3:-$file1}"
    local label2="${4:-$file2}"

    echo "Source: $label1"
    if [[ "$label1" != "$file1" ]]; then
        echo "Source internal file: $file1"
    fi
    echo "Destination: $label2"
    if [[ "$label2" != "$file2" ]]; then
        echo "Destination internal file: $file2"
    fi
    echo "Diff direction: $label2 -> $label1"
    echo ""

    local sorted1="$(_diff_review_mktemp_json)"
    local sorted2="$(_diff_review_mktemp_json)"
    jq -S . "$file1" > "$sorted1"
    jq -S . "$file2" > "$sorted2"

    echo "--- Sorted (semantic differences) ---"
    if command -v difft &> /dev/null; then
        difft "$sorted2" "$sorted1" || true
    else
        diff -u "$sorted2" "$sorted1" || true
    fi

    echo ""

    echo "--- Original (including key order differences) ---"
    if command -v difft &> /dev/null; then
        difft "$file2" "$file1" || true
    else
        diff -u "$file2" "$file1" || true
    fi

    /bin/rm -f "$sorted1" "$sorted2"
}

function json_files_semantically_equal() {
    local file1="$1"
    local file2="$2"
    local sorted1="$(_diff_review_mktemp_json)"
    local sorted2="$(_diff_review_mktemp_json)"

    if ! jq -S . "$file1" > "$sorted1" || ! jq -S . "$file2" > "$sorted2"; then
        /bin/rm -f "$sorted1" "$sorted2"
        return 1
    fi

    diff -q "$sorted1" "$sorted2" > /dev/null 2>&1
    local result=$?
    /bin/rm -f "$sorted1" "$sorted2"
    return $result
}

function _diff_review_state_dir() {
    if [[ -n "${SETTINGFILES_DIFF_REVIEW_DIR:-}" ]]; then
        print -r -- "$SETTINGFILES_DIFF_REVIEW_DIR"
    else
        print -r -- "${XDG_STATE_HOME:-$HOME/.local/state}/SettingFiles/diff-reviews"
    fi
}

function _diff_review_sha256() {
    local hash_output

    if command -v shasum >/dev/null 2>&1; then
        hash_output=$(shasum -a 256) || return 1
        print -r -- "${hash_output%% *}"
    elif command -v sha256sum >/dev/null 2>&1; then
        hash_output=$(sha256sum) || return 1
        print -r -- "${hash_output%% *}"
    else
        python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
    fi
}

function _diff_review_mktemp_json() {
    local tmpdir="${TMPDIR:-/tmp}"
    tmpdir="${tmpdir%/}"
    mktemp "${tmpdir}/settingfiles_diff_review_json.XXXXXX"
}

function _diff_review_file_hash() {
    local file="$1"
    _diff_review_sha256 < "$file"
}

function _diff_review_state_file() {
    local signature="$1"
    print -r -- "$(_diff_review_state_dir)/${signature}.state"
}

function _diff_review_last_reviewed_at() {
    local signature="$1"
    local state_file="$(_diff_review_state_file "$signature")"
    local line

    [[ -f "$state_file" ]] || return 1

    line=$(awk -F= '$1 == "last_reviewed_at" { sub(/^[^=]*=/, ""); print; exit }' "$state_file")
    [[ -n "$line" ]] || return 1
    print -r -- "$line"
}

function _diff_review_record() {
    local signature="$1"
    local state_dir="$(_diff_review_state_dir)"
    local state_file="$state_dir/${signature}.state"
    local timestamp

    mkdir -p "$state_dir" || return 1
    timestamp=$(date '+%Y-%m-%d %H:%M:%S %z')
    {
        print -r -- "signature=$signature"
        print -r -- "last_reviewed_at=$timestamp"
    } >| "$state_file"
}

function _diff_review_smart_merge_auto_enabled() {
    case "${SMART_MERGE_ACTION:-}" in
        overwrite|keep|merge_src|merge_dst)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 署名一致（前回確認時と同じ差分）を検出したときに再度プロンプトを出すか。
# デフォルトは出さない = 自動スキップ。
# SMART_MERGE_ACTION が設定されている場合、そちらが repeated 機構ごとバイパス
# するため本フラグは無視される（make_symlink を除く）。
# 戻り値: 0 = 再プロンプトする / 1 = 自動スキップする
function _diff_review_reprompt_enabled() {
    case "${SETTINGFILES_DIFF_REVIEW_REPROMPT:-}" in
        1|true|TRUE|True|yes|YES|Yes|on|ON)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

function _diff_review_file_signature() {
    local operation="$1"
    local src="$2"
    local dst="$3"
    local src_label="${4:-$src}"
    local dst_label="${5:-$dst}"

    {
        print -r -- "operation=$operation"
        print -r -- "src_label=$src_label"
        print -r -- "dst_label=$dst_label"
        print -r -- "src_sha256=$(_diff_review_file_hash "$src")"
        print -r -- "dst_sha256=$(_diff_review_file_hash "$dst")"
        diff -u --label "$dst_label" --label "$src_label" "$dst" "$src" || true
    } | _diff_review_sha256
}

function _diff_review_json_signature() {
    local operation="$1"
    local src="$2"
    local dst="$3"
    local src_label="${4:-$src}"
    local dst_label="${5:-$dst}"
    local sorted_src="$(_diff_review_mktemp_json)"
    local sorted_dst="$(_diff_review_mktemp_json)"

    if ! jq -S . "$src" > "$sorted_src" || ! jq -S . "$dst" > "$sorted_dst"; then
        /bin/rm -f "$sorted_src" "$sorted_dst"
        _diff_review_file_signature "$operation" "$src" "$dst" "$src_label" "$dst_label"
        return $?
    fi

    {
        print -r -- "operation=$operation"
        print -r -- "src_label=$src_label"
        print -r -- "dst_label=$dst_label"
        print -r -- "--- sorted semantic diff ---"
        diff -u --label "$dst_label.sorted" --label "$src_label.sorted" "$sorted_dst" "$sorted_src" || true
        print -r -- "--- raw diff ---"
        diff -u --label "$dst_label" --label "$src_label" "$dst" "$src" || true
    } | _diff_review_sha256
    local result=$?

    /bin/rm -f "$sorted_src" "$sorted_dst"
    return $result
}

function _diff_review_path_type() {
    local target_path="$1"

    if [[ -L "$target_path" ]]; then
        print -r -- "symlink -> $(readlink "$target_path")"
    elif [[ -d "$target_path" ]]; then
        print -r -- "directory"
    elif [[ -f "$target_path" ]]; then
        print -r -- "file"
    elif [[ -e "$target_path" ]]; then
        print -r -- "other"
    else
        print -r -- "missing"
    fi
}

function _diff_review_path_fingerprint() {
    local target_path="$1"

    if [[ -L "$target_path" ]]; then
        print -r -- "symlink	$(readlink "$target_path")"
    elif [[ -f "$target_path" ]]; then
        print -r -- "file	$(_diff_review_file_hash "$target_path")"
    elif [[ -d "$target_path" ]]; then
        print -r -- "directory"
        (
            cd "$target_path" || exit 1
            find . -print | LC_ALL=C sort | while IFS= read -r item; do
                if [[ "$item" == "." ]]; then
                    continue
                elif [[ -L "$item" ]]; then
                    print -r -- "symlink	$item	$(readlink "$item")"
                elif [[ -f "$item" ]]; then
                    print -r -- "file	$item	$(_diff_review_file_hash "$item")"
                elif [[ -d "$item" ]]; then
                    print -r -- "directory	$item"
                else
                    print -r -- "other	$item"
                fi
            done
        )
    elif [[ -e "$target_path" ]]; then
        print -r -- "other"
    else
        print -r -- "missing"
    fi
}

function _diff_review_symlink_signature() {
    local src="$1"
    local link_path="$2"

    {
        print -r -- "operation=make_symlink"
        print -r -- "link_path=$link_path"
        print -r -- "intended_target=$src"
        print -r -- "source_fingerprint"
        _diff_review_path_fingerprint "$src"
        print -r -- "existing_path_fingerprint"
        _diff_review_path_fingerprint "$link_path"
    } | _diff_review_sha256
}

function _diff_review_show_symlink_change() {
    local src="$1"
    local link_path="$2"
    local src_type="$(_diff_review_path_type "$src")"
    local existing_type="$(_diff_review_path_type "$link_path")"

    echo "Existing path: $link_path"
    echo "Existing type: $existing_type"
    echo "Source path: $src"
    echo "Source type: $src_type"
    echo "Intended symlink: $link_path -> $src"

    if [[ -f "$src" && -f "$link_path" ]]; then
        echo ""
        if diff -q "$link_path" "$src" >/dev/null 2>&1; then
            echo "=== No content differences found ==="
        else
            echo "=== Differences found ==="
            show_file_diff "$src" "$link_path"
        fi
        echo "========================="
    elif [[ -d "$src" && -d "$link_path" ]]; then
        echo ""
        if diff -qr "$link_path" "$src" >/dev/null 2>&1; then
            echo "=== No content differences found ==="
        else
            echo "=== Directory differences found ==="
            echo "Source: $src"
            echo "Destination: $link_path"
            echo "Diff direction: $link_path -> $src"
            echo ""
            if command -v difft &> /dev/null; then
                difft --skip-unchanged --sort-paths "$link_path" "$src" || true
            else
                diff -ru "$link_path" "$src" || true
            fi
        fi
        echo "===================================="
    else
        echo "Comparison unavailable: source is $src_type; existing path is $existing_type."
        echo "Only two regular files or two directories can be compared."
    fi
}

function _ensure_prompt_notify_available() {
    if ! (( ${+functions[notify]} )); then
        source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh" 2>/dev/null || true
    fi
}

function _start_prompt_wait_notification() {
    local message="$1"
    local group="${2:-confirm-prompt}"

    _ensure_prompt_notify_available

    if (( ${+functions[notify]} )); then
        local _title
        if (( ${+functions[build_notification_title]} )); then
            _title=$(build_notification_title "⚠️" "入力待ち")
        else
            _title="入力待ち"
        fi
        notify --tmux-icon "${EMOJI_STATUS_NOTIFICATION:-✋}" "$_title" "$message" "default" "$group" || true
    fi

    return 0
}

function _finish_prompt_wait_notification() {
    if (( ${+functions[remove_tmux_window_icon]} )); then
        remove_tmux_window_icon || true
    fi

    # Herdr環境ではtab/workspaceからも✋を外す（tmuxとHerdrは排他的に動作するため
    # 双方を無条件に呼んでも問題ない）
    if ! (( ${+functions[remove_herdr_status_icon]} )); then
        source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/herdr_status_icon.sh" 2>/dev/null || true
    fi
    if (( ${+functions[remove_herdr_status_icon]} )); then
        remove_herdr_status_icon || true
    fi

    return 0
}

# Resolve SMART_MERGE_ACTION into a normalized action, for non-interactive
# automation of smart_merge_json/smart_copy prompts.
# Usage: action=$(_smart_merge_resolved_action)
# Returns (stdout): overwrite|keep|merge_src|merge_dst, or empty string
#   when unset (fall through to interactive prompt).
# Invalid values print a warning to stderr and also fall through to empty
# (interactive), rather than aborting the whole script.
function _smart_merge_resolved_action() {
    local a="${SMART_MERGE_ACTION:-}"
    [[ -z "$a" ]] && return 0
    case "$a" in
        overwrite|keep|merge_src|merge_dst)
            echo "$a"
            ;;
        *)
            echo "⚠️  Invalid SMART_MERGE_ACTION='$a' (expected: overwrite|keep|merge_src|merge_dst). Falling back to interactive." >&2
            ;;
    esac
}

# Prompt user for copy action (overwrite or skip)
function prompt_copy_action() {
    local notification_message="$1"
    local choice

    local _auto
    _auto=$(_smart_merge_resolved_action)
    if [[ -n "$_auto" ]]; then
        [[ "$_auto" == "overwrite" ]] && return 0
        return 1
    fi

    if [[ -n "$notification_message" ]]; then
        _start_prompt_wait_notification "$notification_message" "smart-merge-json-prompt"
    fi

    echo ""
    echo -n "Overwrite? [o]verwrite / [s]kip (default: s): "
    read -r choice
    if [[ -n "$notification_message" ]]; then
        _finish_prompt_wait_notification
    fi

    case "$choice" in
        o|O|overwrite)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Prompt user for merge action (overwrite, keep, merge with priority)
function prompt_merge_action() {
    local notification_message="${1:-smart_merge_json action required}"
    local choice

    local _auto
    _auto=$(_smart_merge_resolved_action)
    if [[ -n "$_auto" ]]; then
        echo "$_auto"
        return 0
    fi

    _start_prompt_wait_notification "$notification_message" "smart-merge-json-prompt"
    echo "" >&2
    echo "[o] Overwrite: Replace destination with source" >&2
    echo "[k] Keep: Keep destination as is (skip)" >&2
    echo "[m] Merge (source priority): Merge with source winning conflicts" >&2
    echo "[d] Merge (destination priority): Merge with destination winning conflicts" >&2
    echo -n "Choose action (default: k): " >&2
    read -r choice
    _finish_prompt_wait_notification

    case "$choice" in
        o|O|overwrite)
            echo "overwrite"
            ;;
        m|M)
            echo "merge_src"
            ;;
        d|D)
            echo "merge_dst"
            ;;
        *)
            echo "keep"
            ;;
    esac
}

function _diff_review_prompt_repeated_copy() {
    local signature="$1"
    local timestamp="$2"
    local notification_message="$3"
    local dst_label="$4"
    local choice

    if [[ -n "$notification_message" ]]; then
        _start_prompt_wait_notification "$notification_message" "smart-merge-json-prompt"
    fi

    if [[ -n "$dst_label" ]]; then
        echo "前回確認時と同じ差分です: $timestamp ($dst_label)" >&2
    else
        echo "前回確認時と同じ差分です: $timestamp" >&2
    fi
    echo -n "[s]kip / [v]iew diff / [o]verwrite (default: s): " >&2
    _diff_review_record "$signature"
    read -r choice

    if [[ -n "$notification_message" ]]; then
        _finish_prompt_wait_notification
    fi

    case "$choice" in
        v|V|view)
            echo "view"
            ;;
        o|O|overwrite)
            echo "overwrite"
            ;;
        *)
            echo "skip"
            ;;
    esac
}

function _diff_review_prompt_repeated_merge() {
    local signature="$1"
    local timestamp="$2"
    local notification_message="${3:-smart_merge_json action required}"
    local dst_label="$4"
    local choice

    _start_prompt_wait_notification "$notification_message" "smart-merge-json-prompt"
    if [[ -n "$dst_label" ]]; then
        echo "前回確認時と同じ差分です: $timestamp ($dst_label)" >&2
    else
        echo "前回確認時と同じ差分です: $timestamp" >&2
    fi
    echo -n "[k]eep / [v]iew diff / [o]verwrite / [m]erge source priority / [d]merge destination priority (default: k): " >&2
    _diff_review_record "$signature"
    read -r choice
    _finish_prompt_wait_notification

    case "$choice" in
        v|V|view)
            echo "view"
            ;;
        o|O|overwrite)
            echo "overwrite"
            ;;
        m|M)
            echo "merge_src"
            ;;
        d|D)
            echo "merge_dst"
            ;;
        *)
            echo "keep"
            ;;
    esac
}

function _diff_review_prompt_repeated_symlink() {
    local signature="$1"
    local timestamp="$2"
    local src="$3"
    local link_path="$4"
    local choice

    _start_prompt_wait_notification "make_symlink overwrite required: $link_path -> $src" "confirm-prompt"
    echo "前回確認時と同じ差分です: $timestamp ($link_path)" >&2
    echo -n "[s]kip / [v]iew change / [o]verwrite (default: s): " >&2
    _diff_review_record "$signature"
    read -r choice
    _finish_prompt_wait_notification

    case "$choice" in
        v|V|view)
            echo "view"
            ;;
        o|O|overwrite)
            echo "overwrite"
            ;;
        *)
            echo "skip"
            ;;
    esac
}

# Unified confirmation prompt with optional notification.
# Usage: confirm "メッセージ" [--default-no] [--no-notify] [--single-key] [--no-cancel-msg] [--smart-merge-gated]
# Returns: 0 = yes, 1 = no/cancel
#   --default-no         Default answer is No (requires explicit y/Y)
#   --no-notify          Suppress the macOS notification
#   --single-key         Use read -k 1 (no Enter needed), implies --default-no
#   --no-cancel-msg      Suppress the "❌ キャンセルされました" message on rejection
#   --smart-merge-gated  Opt in to SMART_MERGE_ACTION auto-answering (smart_merge_json
#                        internal use only; plain confirm() calls never read that env var)
function confirm() {
    local message="$1"
    shift

    local default_yes=true
    local send_notify=true
    local single_key=false
    local cancel_msg=true
    local smart_merge_gated=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --default-no)        default_yes=false ;;
            --no-notify)         send_notify=false ;;
            --single-key)        single_key=true; default_yes=false ;;
            --no-cancel-msg)     cancel_msg=false ;;
            --smart-merge-gated) smart_merge_gated=true ;;
        esac
        shift
    done

    if $smart_merge_gated; then
        local _auto
        _auto=$(_smart_merge_resolved_action)
        case "$_auto" in
            merge_src|merge_dst)
                return 0
                ;;
            overwrite|keep)
                return 1
                ;;
        esac
    fi

    local prompt_hint
    if $default_yes; then
        prompt_hint="[Y/n]"
    else
        prompt_hint="[y/N]"
    fi

    if $send_notify; then
        _start_prompt_wait_notification "$message" "confirm-prompt"
    fi

    local reply
    if $single_key; then
        read -k 1 -r "reply?${message} ${prompt_hint} "
        echo ""
    else
        echo -n "${message} ${prompt_hint} "
        read -r reply
    fi
    _finish_prompt_wait_notification

    if $default_yes; then
        [[ "$reply" =~ ^[Yy]?$ ]] && return 0
    else
        [[ "$reply" =~ ^[Yy]$ ]] && return 0
    fi

    $cancel_msg && echo "❌ キャンセルされました"
    return 1
}

# Prompt for freeform text input with optional notification.
# Usage: result=$(prompt_input "メッセージ")
#   or:  prompt_input "メッセージ" var_name [--no-notify]
function prompt_input() {
    local message="$1"
    local var_name="$2"
    local send_notify=true

    [[ "$var_name" == "--no-notify" ]] && send_notify=false && var_name=""
    [[ "$3" == "--no-notify" ]] && send_notify=false

    if $send_notify; then
        _start_prompt_wait_notification "$message" "confirm-prompt"
    fi

    local reply
    read -r "reply?${message} "
    _finish_prompt_wait_notification

    if [[ -n "$var_name" ]]; then
        eval "$var_name=\$reply"
    else
        echo "$reply"
    fi
}

# Smart copy: check diff before overwriting
function smart_copy() {
    local src="$1"
    local dst="$2"

    if [[ -z "$src" || -z "$dst" ]]; then
        echo "Usage: smart_copy <source> <destination>"
        return 1
    fi

    # Check if source file exists
    if [[ ! -f "$src" ]]; then
        echo "Error: Source file not found: $src" >&2
        return 1
    fi

    # Check if destination is a directory (file path required)
    if [[ -d "$dst" ]]; then
        echo "Error: Destination is a directory, file path required: $dst" >&2
        return 1
    fi

    # Create destination directory if it doesn't exist
    local target_dir="$(dirname "$dst")"
    if [[ ! -d "$target_dir" ]]; then
        echo "mkdir -p $target_dir"
        mkdir -p "$target_dir"
    fi

    # If destination doesn't exist, just copy
    if [[ ! -f "$dst" ]]; then
        echo "cp \"$src\" \"$dst\""
        cp "$src" "$dst"
        return $?
    fi

    # Check for differences
    if diff -q "$src" "$dst" > /dev/null 2>&1; then
        echo "✓ Files are identical, skipping: $dst"
        return 0
    fi

    local review_signature=""
    local last_reviewed_at=""
    local repeated_action=""

    review_signature=$(_diff_review_file_signature "smart_copy" "$src" "$dst" 2>/dev/null || true)
    if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
        last_reviewed_at=$(_diff_review_last_reviewed_at "$review_signature" 2>/dev/null || true)
        if [[ -n "$last_reviewed_at" ]]; then
            if _diff_review_reprompt_enabled; then
                repeated_action=$(_diff_review_prompt_repeated_copy "$review_signature" "$last_reviewed_at" "" "$dst")
            else
                repeated_action="skip"
            fi
            case "$repeated_action" in
                overwrite)
                    echo "cp \"$src\" \"$dst\""
                    cp "$src" "$dst"
                    return $?
                    ;;
                skip)
                    echo "Skipped: $dst (前回確認時と同じ差分です: $last_reviewed_at)"
                    return 0
                    ;;
                view)
                    ;;
            esac
        fi
    fi

    # Show differences and prompt user
    echo ""
    echo "=== Differences found ==="
    show_file_diff "$src" "$dst"
    echo "========================="

    if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
        _diff_review_record "$review_signature"
    fi

    if prompt_copy_action; then
        echo "cp \"$src\" \"$dst\""
        cp "$src" "$dst"
        return $?
    else
        echo "Skipped: $dst"
        return 0
    fi
}

# Smart merge JSON: intelligently merge JSON files with conflict resolution
function smart_merge_json() {
    local src="$1"
    local dst="$2"
    local src_label="${3:-$src}"
    local dst_label="${4:-$dst}"

    if [[ -z "$src" || -z "$dst" ]]; then
        echo "Usage: smart_merge_json <source> <destination> [source_label] [destination_label]"
        return 1
    fi

    # Check if source file exists
    if [[ ! -f "$src" ]]; then
        echo "Error: Source file not found: $src_label" >&2
        return 1
    fi

    # Check if destination is a directory (file path required)
    if [[ -d "$dst" ]]; then
        echo "Error: Destination is a directory, file path required: $dst_label" >&2
        return 1
    fi

    # Create destination directory if it doesn't exist
    local target_dir="$(dirname "$dst")"
    if [[ ! -d "$target_dir" ]]; then
        echo "mkdir -p $target_dir"
        mkdir -p "$target_dir"
    fi

    # If destination doesn't exist, just copy
    if [[ ! -f "$dst" ]]; then
        echo "cp \"$src\" \"$dst\""
        cp "$src" "$dst"
        return $?
    fi

    # Check for differences
    if diff -q "$src" "$dst" > /dev/null 2>&1; then
        echo "✓ Files are identical, skipping: $dst_label"
        return 0
    fi

    # Validate JSON files
    local src_valid=true
    local dst_valid=true

    if ! jq empty "$src" > /dev/null 2>&1; then
        src_valid=false
    fi

    if ! jq empty "$dst" > /dev/null 2>&1; then
        dst_valid=false
    fi

    # Check if top-level is array (cannot be merged reliably)
    local src_is_array=false
    local dst_is_array=false

    if $src_valid && [[ "$(jq -r 'type' "$src")" == "array" ]]; then
        src_is_array=true
    fi

    if $dst_valid && [[ "$(jq -r 'type' "$dst")" == "array" ]]; then
        dst_is_array=true
    fi

    # Fallback to smart_copy if JSON is invalid or is array
    if ! $src_valid || ! $dst_valid || $src_is_array || $dst_is_array; then
        if ! $src_valid || ! $dst_valid; then
            if ! $src_valid; then
                echo "⚠️  Invalid JSON: $src_label" >&2
            fi
            if ! $dst_valid; then
                echo "⚠️  Invalid JSON: $dst_label" >&2
            fi
            echo "Falling back to overwrite/skip mode" >&2
        elif $src_is_array || $dst_is_array; then
            echo "⚠️  Top-level array detected, merge not supported" >&2
        fi

        # merge_src/merge_dst implies the caller wants a real merge, which is
        # not possible here (invalid JSON or top-level array). Surface this
        # as a failure instead of silently skipping, so it doesn't go unnoticed.
        local _auto_fallback
        _auto_fallback=$(_smart_merge_resolved_action)
        if [[ "$_auto_fallback" == "merge_src" || "$_auto_fallback" == "merge_dst" ]]; then
            echo "❌ SMART_MERGE_ACTION=$_auto_fallback requested but merge is not possible (invalid JSON or top-level array): $dst_label" >&2
            return 1
        fi

        local review_signature=""
        local last_reviewed_at=""
        local repeated_action=""

        review_signature=$(_diff_review_file_signature "smart_merge_json_fallback" "$src" "$dst" "$src_label" "$dst_label" 2>/dev/null || true)
        if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
            last_reviewed_at=$(_diff_review_last_reviewed_at "$review_signature" 2>/dev/null || true)
            if [[ -n "$last_reviewed_at" ]]; then
                if _diff_review_reprompt_enabled; then
                    repeated_action=$(_diff_review_prompt_repeated_copy "$review_signature" "$last_reviewed_at" "smart_merge_json overwrite/skip required: $src_label -> $dst_label" "$dst_label")
                else
                    repeated_action="skip"
                fi
                case "$repeated_action" in
                    overwrite)
                        echo "Applying source to destination: $src_label -> $dst_label"
                        echo "cp \"$src\" \"$dst\""
                        cp "$src" "$dst"
                        return $?
                        ;;
                    skip)
                        echo "Skipped: $dst_label (前回確認時と同じ差分です: $last_reviewed_at)"
                        return 0
                        ;;
                    view)
                        ;;
                esac
            fi
        fi

        echo ""
        echo "=== Differences found ==="
        show_file_diff "$src" "$dst" "$src_label" "$dst_label"
        echo "========================="

        if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
            _diff_review_record "$review_signature"
        fi

        if prompt_copy_action "smart_merge_json overwrite/skip required: $src_label -> $dst_label"; then
            echo "Applying source to destination: $src_label -> $dst_label"
            echo "cp \"$src\" \"$dst\""
            cp "$src" "$dst"
            return $?
        else
            echo "Skipped: $dst_label"
            return 0
        fi
    fi

    # Semantic JSON comparison: skip if only key order/whitespace differs
    if json_files_semantically_equal "$src" "$dst"; then
        echo "✓ JSON is semantically identical, skipping: $dst_label"
        return 0
    fi

    local review_signature=""
    local last_reviewed_at=""
    local action=""

    review_signature=$(_diff_review_json_signature "smart_merge_json" "$src" "$dst" "$src_label" "$dst_label" 2>/dev/null || true)
    if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
        last_reviewed_at=$(_diff_review_last_reviewed_at "$review_signature" 2>/dev/null || true)
        if [[ -n "$last_reviewed_at" ]]; then
            if _diff_review_reprompt_enabled; then
                action=$(_diff_review_prompt_repeated_merge "$review_signature" "$last_reviewed_at" "smart_merge_json merge action required: $src_label -> $dst_label" "$dst_label")
            else
                # 下流の case は overwrite|keep|merge_src|merge_dst のみを受けるため
                # skip ではなく keep を入れる
                action="keep"
                echo "前回確認時と同じ差分のため自動スキップしました: $last_reviewed_at ($dst_label)"
            fi
        fi
    fi

    if [[ -z "$action" || "$action" == "view" ]]; then
        echo ""
        echo "=== Differences found ==="
        show_json_diff "$src" "$dst" "$src_label" "$dst_label"
        echo "========================="

        if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
            _diff_review_record "$review_signature"
        fi

        action=$(prompt_merge_action "smart_merge_json merge action required: $src_label -> $dst_label")
    fi

    case "$action" in
        overwrite)
            echo "Applying source to destination: $src_label -> $dst_label"
            echo "cp \"$src\" \"$dst\""
            cp "$src" "$dst"
            return $?
            ;;
        keep)
            echo "Skipped: $dst_label"
            return 0
            ;;
        merge_src|merge_dst)
            # Create temporary file for merge result
            local tmp_file="$(_diff_review_mktemp_json)"

            # deepmerge: オブジェクトは再帰的にマージ、配列は初出順を保ったunionで結合する。
            # 例外: mcpServers.*.args と _disabledMcpServers.*.args はunionせず優先側の値で置換する。
            # CLI引数は位置依存のため、マージやソートをするとコマンドが壊れるため。
            # path は再帰中の現在キーパスを追跡し、この例外判定に使用する。
            local jq_deepmerge='
def stable_unique:
  reduce .[] as $item ([]; if any(.[]; . == $item) then . else . + [$item] end);

def deepmerge(a; b; path):
  if (a | type) == "object" and (b | type) == "object" then
    reduce ([ (a | keys[]), (b | keys[]) ] | unique)[] as $k ({};
      if (a | has($k)) and (b | has($k)) then . + {($k): deepmerge(a[$k]; b[$k]; path + [$k])}
      elif (a | has($k)) then . + {($k): a[$k]}
      else . + {($k): b[$k]}
      end
    )
  elif (a | type) == "array" and (b | type) == "array" then
    if (path | length >= 3) and (path[-1] == "args") and (path[-3] | test("^(mcpServers|_disabledMcpServers|mcp_servers)$"))
    then b
    else [a[], b[]] | stable_unique
    end
  else b
  end;
. as $f | deepmerge($f[0]; $f[1]; [])
'

            # Perform merge based on priority
            if [[ "$action" == "merge_src" ]]; then
                echo "Merging with source priority..."
                jq -s "$jq_deepmerge" "$dst" "$src" > "$tmp_file"
            else
                echo "Merging with destination priority..."
                jq -s "$jq_deepmerge" "$src" "$dst" > "$tmp_file"
            fi

            # Check if merge was successful
            if [[ $? -ne 0 ]] || ! jq empty "$tmp_file" > /dev/null 2>&1; then
                echo "Error: Merge failed" >&2
                /bin/rm -f "$tmp_file"
                return 1
            fi

            # Skip if merge result is identical to current destination
            if diff -q "$tmp_file" "$dst" > /dev/null 2>&1; then
                echo "✓ Merge result is identical to current file, skipping: $dst_label"
                /bin/rm -f "$tmp_file"
                return 0
            fi

            if json_files_semantically_equal "$tmp_file" "$dst"; then
                echo "✓ Merge result is semantically identical to current file, skipping: $dst_label"
                /bin/rm -f "$tmp_file"
                return 0
            fi

            # Show merge result preview
            echo ""
            echo "=== Merge result preview ==="
            show_json_diff "$tmp_file" "$dst" "Merge result for $dst_label" "$dst_label"
            echo "============================"

            # Final confirmation
            echo ""
            if confirm "Apply merge?" --default-no --no-cancel-msg --smart-merge-gated; then
                echo "Applying merge result to destination: $dst_label"
                echo "cp \"$tmp_file\" \"$dst\""
                cp "$tmp_file" "$dst"
                local result=$?
                /bin/rm -f "$tmp_file"
                return $result
            else
                echo "Merge cancelled"
                /bin/rm -f "$tmp_file"
                return 0
            fi
            ;;
    esac
}

function validate_toml_strict() {
    local file="$1"
    local label="${2:-$file}"

    if ! command -v python3 >/dev/null 2>&1; then
        echo "✗ python3 not found. Strict TOML validation requires python3." >&2
        return 1
    fi

    python3 - "$file" "$label" <<'PY'
import sys

path = sys.argv[1]
label = sys.argv[2]

try:
    import tomllib
except ModuleNotFoundError:
    print("Error: Python 3.11+ is required for strict TOML validation.", file=sys.stderr)
    sys.exit(1)

try:
    with open(path, "rb") as file:
        tomllib.load(file)
except Exception as error:
    print(f"Error: Invalid TOML: {label}", file=sys.stderr)
    print(f"       {error}", file=sys.stderr)
    sys.exit(1)
PY
}

# TOML ファイルを対話形式でマージする（dasel 経由で TOML↔JSON 変換し、smart_merge_json に委譲）
# Usage: smart_merge_toml <source> <destination>
# - source: リポジトリ側のテンプレート TOML
# - destination: ユーザー環境側の TOML（存在しない場合はコピー）
# 制約: dasel が必要（brew install dasel）。コメントとキー順序はラウンドトリップで失われる。
function smart_merge_toml() {
    local src="$1" dst="$2"

    if [[ -z "$src" || -z "$dst" ]]; then
        echo "Usage: smart_merge_toml <source> <destination>"
        return 1
    fi

    if ! command -v dasel >/dev/null 2>&1; then
        echo "✗ dasel not found. Install with: brew install dasel" >&2
        return 1
    fi

    if [[ ! -f "$src" ]]; then
        echo "Error: Source file not found: $src" >&2
        return 1
    fi

    if ! validate_toml_strict "$src"; then
        return 1
    fi

    local target_dir="$(dirname "$dst")"
    if [[ ! -d "$target_dir" ]]; then
        mkdir -p "$target_dir"
    fi

    # dst が存在しない場合はコピーして終了
    if [[ ! -f "$dst" ]]; then
        echo "cp \"$src\" \"$dst\""
        cp "$src" "$dst"
        return $?
    fi

    if ! validate_toml_strict "$dst"; then
        return 1
    fi

    local tmpdir
    tmpdir=$(mktemp -d /tmp/smart_merge_toml_XXXXXX)
    local src_json="${tmpdir}/src.json"
    local dst_json="${tmpdir}/dst.json"
    local dst_json_before="${tmpdir}/before.json"

    # TOML → JSON 変換
    if ! dasel query -i toml -o json --root < "$src" > "$src_json" 2>/dev/null; then
        echo "Error: Failed to parse TOML: $src" >&2
        /bin/rm -rf "$tmpdir"
        return 1
    fi
    if ! dasel query -i toml -o json --root < "$dst" > "$dst_json" 2>/dev/null; then
        echo "Error: Failed to parse TOML: $dst" >&2
        /bin/rm -rf "$tmpdir"
        return 1
    fi
    cp "$dst_json" "$dst_json_before"

    # JSON マージ（対話 UI は smart_merge_json に委譲）
    smart_merge_json "$src_json" "$dst_json" "$src" "$dst"
    local rc=$?

    # dst_json が変更された場合のみ JSON→TOML 書き戻し
    if [[ $rc -eq 0 ]] && ! diff -q "$dst_json" "$dst_json_before" > /dev/null 2>&1; then
        dasel query -i json -o toml --root < "$dst_json" > "$dst"
    fi

    /bin/rm -rf "$tmpdir"
    return $rc
}

function setup_ai_mcp() {
    local mode="install"
    if [[ "$1" == "update" || "$1" == "--update" ]]; then
        mode="update"
    fi

    if [[ "${AI_MCP_SETUP_DONE:-}" == "$mode" ]]; then
        echo "✓ Shared AI MCP packages already handled for this run: $mode"
        return 0
    fi

    local repo_root="${Repo:-$HOME/Desktop/repository/SettingFiles/}"
    local mcp_dir="${repo_root%/}/ai/common/mcp"
    local link_dest="$HOME/.config/ai-mcp"
    local packages=()

    if [[ ! -d "$mcp_dir" ]]; then
        echo "Error: Shared AI MCP directory not found: $mcp_dir" >&2
        return 1
    fi

    local mcp_node
    mcp_node="$(zsh "$mcp_dir/bin/global-node" --print-node)" || return $?
    local mcp_node_dir="${mcp_node:h}"

    if [[ "$mode" == "update" || ! -f "$mcp_dir/package-lock.json" ]]; then
        echo "Updating shared AI MCP packages..."
        local latest_packages=("${packages[@]/%/@latest}")
        PATH="$mcp_node_dir:$PATH" npm install --prefix "$mcp_dir" "${latest_packages[@]}"
    else
        echo "Installing shared AI MCP packages..."
        PATH="$mcp_node_dir:$PATH" npm install --prefix "$mcp_dir"
    fi
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        return $rc
    fi

    make_symlink "$mcp_dir" "$link_dest"

    if [[ -d "$link_dest/bin" ]]; then
        chmod +x "$link_dest"/bin/*(N)
    fi

    export AI_MCP_SETUP_DONE="$mode"
}
