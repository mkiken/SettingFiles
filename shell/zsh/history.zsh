#!/bin/zsh
# History configuration for zsh

## Command history configuration
#
export HISTFILE=$HOME/.zsh_history
export HISTSIZE=100000        # メモリ上の履歴リストに保存されるイベントの最大数
export SAVEHIST=100000        # 履歴ファイルに保存されるイベントの最大数

setopt hist_expire_dups_first # 履歴を切り詰める際に、重複する最も古いイベントから消す
setopt hist_ignore_all_dups   # 履歴が重複した場合に古い履歴を削除する
setopt hist_save_no_dups      # 履歴ファイルに書き出す際、新しいコマンドと重複する古いコマンドは切り捨てる
setopt share_history          # 全てのセッションで履歴を共有する
setopt hist_reduce_blanks     # 余分な空白は詰めて記録
setopt hist_find_no_dups      # 履歴検索中、(連続してなくとも)重複を飛ばす
setopt inc_append_history     # コマンド実行時にすぐ履歴ファイルに追記