#!/bin/zsh

function make_symlink () {
  # リンク先のディレクトリを取得
  local target_dir="$(dirname "$2")"

  # ディレクトリが存在しない場合は作成
  if [[ ! -d "$target_dir" ]]; then
    echo "mkdir -p $target_dir"
    mkdir -p "$target_dir"
  fi

  echo "ln -si $1 $2"
  ln -si "$1" "$2"
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

    echo "Source: $file1"
    echo "Destination: $file2"
    echo ""

    # Use difft if available, otherwise use regular diff
    if command -v difft &> /dev/null; then
        difft "$file2" "$file1" || true
    else
        diff -u "$file2" "$file1" || true
    fi
}

# Prompt user for copy action (overwrite or skip)
function prompt_copy_action() {
    local choice

    echo ""
    echo -n "Overwrite? [o]verwrite / [s]kip (default: s): "
    read -r choice

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
    local choice

    echo "" >&2
    echo "[o] Overwrite: Replace destination with source" >&2
    echo "[k] Keep: Keep destination as is (skip)" >&2
    echo "[m] Merge (source priority): Merge with source winning conflicts" >&2
    echo "[d] Merge (destination priority): Merge with destination winning conflicts" >&2
    echo -n "Choose action (default: k): " >&2
    read -r choice

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

    if [[ -z "$src" || -z "$dst" ]]; then
        echo "Usage: smart_merge_json <source> <destination>"
        return 1
    fi

    # Check if source file exists
    if [[ ! -f "$src" ]]; then
        echo "Error: Source file not found: $src" >&2
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
                echo "⚠️  Invalid JSON: $src" >&2
            fi
            if ! $dst_valid; then
                echo "⚠️  Invalid JSON: $dst" >&2
            fi
            echo "Falling back to overwrite/skip mode" >&2
        elif $src_is_array || $dst_is_array; then
            echo "⚠️  Top-level array detected, merge not supported" >&2
        fi

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
    fi

    # Show differences
    echo ""
    echo "=== Differences found ==="
    show_file_diff "$src" "$dst"
    echo "========================="

    # Prompt for action
    local action=$(prompt_merge_action)

    case "$action" in
        overwrite)
            echo "cp \"$src\" \"$dst\""
            cp "$src" "$dst"
            return $?
            ;;
        keep)
            echo "Skipped: $dst"
            return 0
            ;;
        merge_src|merge_dst)
            # Create temporary file for merge result
            local tmp_file=$(mktemp)

            # Perform merge based on priority
            if [[ "$action" == "merge_src" ]]; then
                echo "Merging with source priority..."
                jq -s '.[0] * .[1]' "$dst" "$src" > "$tmp_file" 2>&1
            else
                echo "Merging with destination priority..."
                jq -s '.[0] * .[1]' "$src" "$dst" > "$tmp_file" 2>&1
            fi

            # Check if merge was successful
            if [[ $? -ne 0 ]] || ! jq empty "$tmp_file" > /dev/null 2>&1; then
                echo "Error: Merge failed" >&2
                /bin/rm -f "$tmp_file"
                return 1
            fi

            # Show merge result preview
            echo ""
            echo "=== Merge result preview ==="
            show_file_diff "$tmp_file" "$dst"
            echo "============================"

            # Final confirmation
            echo ""
            echo -n "Apply merge? [y/n] (default: n): "
            local confirm
            read -r confirm

            if [[ "$confirm" =~ ^[yY]$ ]]; then
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

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"