#!/usr/local/bin/zsh

# Filter設定ファイルのディレクトリ
FILTER_DIR="${0:A:h}"

# 分割されたfilter設定ファイルを読み込む
source_and_zcompile_if_needed "${FILTER_DIR}/base.zsh"
source_and_zcompile_if_needed "${FILTER_DIR}/git.zsh"
source_and_zcompile_if_needed "${FILTER_DIR}/github.zsh"
source_and_zcompile_if_needed "${FILTER_DIR}/file.zsh"
source_and_zcompile_if_needed "${FILTER_DIR}/docker.zsh"