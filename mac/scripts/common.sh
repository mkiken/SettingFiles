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

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"