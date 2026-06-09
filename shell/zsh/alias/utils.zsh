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

    if confirm "シンボリックリンクではない既存パスがあります: $link_path。$src へのsymlinkで上書きしますか？" --default-no --no-cancel-msg; then
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

    local sorted1=$(mktemp).json
    local sorted2=$(mktemp).json
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
    local sorted1=$(mktemp).json
    local sorted2=$(mktemp).json

    if ! jq -S . "$file1" > "$sorted1" || ! jq -S . "$file2" > "$sorted2"; then
        /bin/rm -f "$sorted1" "$sorted2"
        return 1
    fi

    diff -q "$sorted1" "$sorted2" > /dev/null 2>&1
    local result=$?
    /bin/rm -f "$sorted1" "$sorted2"
    return $result
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
        notify "$_title" "$message" "default" "$group" || true
    fi

    if (( ${+functions[update_tmux_window_name]} )); then
        update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION:-✋}" || true
    fi

    return 0
}

function _finish_prompt_wait_notification() {
    if (( ${+functions[remove_tmux_window_icon]} )); then
        remove_tmux_window_icon || true
    fi

    return 0
}

# Prompt user for copy action (overwrite or skip)
function prompt_copy_action() {
    local notification_message="$1"
    local choice

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

# Unified confirmation prompt with optional notification.
# Usage: confirm "メッセージ" [--default-no] [--no-notify] [--single-key] [--no-cancel-msg]
# Returns: 0 = yes, 1 = no/cancel
#   --default-no     Default answer is No (requires explicit y/Y)
#   --no-notify      Suppress the macOS notification
#   --single-key     Use read -k 1 (no Enter needed), implies --default-no
#   --no-cancel-msg  Suppress the "❌ キャンセルされました" message on rejection
function confirm() {
    local message="$1"
    shift

    local default_yes=true
    local send_notify=true
    local single_key=false
    local cancel_msg=true

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --default-no)    default_yes=false ;;
            --no-notify)     send_notify=false ;;
            --single-key)    single_key=true; default_yes=false ;;
            --no-cancel-msg) cancel_msg=false ;;
        esac
        shift
    done

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

    # Show differences and prompt user
    echo ""
    echo "=== Differences found ==="
    show_file_diff "$src" "$dst"
    echo "========================="

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

        echo ""
        echo "=== Differences found ==="
        show_file_diff "$src" "$dst" "$src_label" "$dst_label"
        echo "========================="

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

    # Show differences
    echo ""
    echo "=== Differences found ==="
    show_json_diff "$src" "$dst" "$src_label" "$dst_label"
    echo "========================="

    # Prompt for action
    local action=$(prompt_merge_action "smart_merge_json merge action required: $src_label -> $dst_label")

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
            local tmp_file=$(mktemp).json

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
            if confirm "Apply merge?" --default-no --no-cancel-msg; then
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
    local packages=(
        "@21st-dev/magic"
        "@modelcontextprotocol/server-sequential-thinking"
        "@morphllm/morphmcp"
        "@playwright/mcp"
        "@upstash/context7-mcp"
        "chrome-devtools-mcp"
        "tavily-mcp"
    )

    if [[ ! -d "$mcp_dir" ]]; then
        echo "Error: Shared AI MCP directory not found: $mcp_dir" >&2
        return 1
    fi

    if [[ "$mode" == "update" || ! -f "$mcp_dir/package-lock.json" ]]; then
        echo "Updating shared AI MCP packages..."
        local latest_packages=("${packages[@]/%/@latest}")
        npm install --prefix "$mcp_dir" "${latest_packages[@]}"
    else
        echo "Installing shared AI MCP packages..."
        npm install --prefix "$mcp_dir"
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
