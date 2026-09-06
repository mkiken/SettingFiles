#!/bin/bash

# herdr-zoxide の zoxide-picker.sh をログインシェル経由で起動するランチャー。
# Herdr はプラグイン/ポップアップの子プロセスの PATH を /usr/bin:/bin:/usr/sbin:/sbin へ
# 剥ぎ取るため、upstream の picker が依存する zoxide / fzf (Homebrew 配下) を解決できず
# "herdr-zoxide requires: zoxide" で即終了する。config.toml 側で zsh -ilc を挟んで
# PATH を復元した上で、このスクリプトが picker 本体へ橋渡しする。

set -euo pipefail

herdr_bin="${HERDR_BIN_PATH:-herdr}"

# インストール先ディレクトリ名はハッシュ付き (herdr-zoxide-<hash>) なのでハードコードせず
# plugin list から解決する。
plugin_root="$("$herdr_bin" plugin list --json 2>/dev/null \
  | jq -r '.result.plugins[]? | select(.plugin_id == "herdr-zoxide") | .plugin_root // empty')" || plugin_root=""

if [[ -z "$plugin_root" ]]; then
    echo "herdr-zoxide plugin is not installed; zoxide picker was not started" >&2
    exit 1
fi

picker="${plugin_root}/zoxide-picker.sh"
if [[ ! -f "$picker" ]]; then
    echo "herdr-zoxide picker is unavailable: ${picker}" >&2
    exit 1
fi

# picker は set -u 下で HERDR_PLUGIN_CONFIG_DIR を無条件参照するため、未設定だと即死する。
config_dir="$("$herdr_bin" plugin config-dir herdr-zoxide 2>/dev/null)" || config_dir=""
export HERDR_PLUGIN_CONFIG_DIR="${config_dir:-${HOME}/.config/herdr/plugins/config/herdr-zoxide}"

# 剥ぎ取られた環境は LANG を欠くことがあり、多バイトのディレクトリ名表示が壊れる。
export LANG="${LANG:-en_US.UTF-8}"

# 既知の upstream 制限: --no-preview を渡すと picker の fzf_args が空配列のまま
# "${fzf_args[@]}" に展開され、macOS 標準の bash 3.2 では set -u が unbound variable で
# 落ちる (bash 4.4 で緩和された挙動)。引数なしの既定経路はプレビューが自動検出されるため
# この行を踏まない。
exec bash "$picker" "$@"
