#!/bin/zsh

## Completion configuration
# Completions should be configured before compinit

# ファイル補完候補に色を付ける
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}

#from http://qiita.com/items/ed2d36698a5cc314557d
# fzf-tabを使用する場合はmenu noが推奨されるため、ここはコメントアウトしておく
# zstyle ':completion:*:default' menu select=2
zstyle ':completion:*' verbose yes
# zstyle ':completion:*' completer _expand _complete _match _prefix _approximate _list _history
zstyle ':completion:*:messages' format '%F{YELLOW}%d'$DEFAULT
zstyle ':completion:*:warnings' format '%F{RED}No matches for:''%F{YELLOW} %d'$DEFAULT
zstyle ':completion:*:descriptions' format '%F{YELLOW}completing %B%d%b'$DEFAULT
zstyle ':completion:*:options' description 'yes'
zstyle ':completion:*:descriptions' format '%F{yellow}Completing %B%d%b%f'$DEFAULT
zstyle ':completion:*:corrections' format ' %F{green}-- %d (errors: %e) --%f'

# マッチ種別を別々に表示
zstyle ':completion:*' group-name ''

# セパレータを設定する
zstyle ':completion:*' list-separator '-->'
zstyle ':completion:*:manuals' separate-sections true

# 補完機能で大文字小文字を区別しないよう(case insensitive)にする
# 1. 大文字小文字を区別しない
# 2. 途中の文字でもマッチさせる (partial word)
# 3. 曖昧マッチ (fuzzy)
#http://nukesaq88.hatenablog.com/entry/2013/04/18/183335
zstyle ':completion:*' matcher-list \
    'm:{a-zA-Z}={A-Za-z}' \
    'r:|[._-]=* r:|=*' \
    'l:|=* r:|=*'

# キャッシュを有効化
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/compcache"

# manの補完をセクション番号別に表示させる
zstyle ':completion:*:manuals' separate-sections true

# 変数の添字を補完する
zstyle ':completion:*:*:-subscript-:*' tag-order indexes parameters

# http://qiita.com/mollifier/items/33bda290fe3c0ae7b3bb
zstyle ':completion:*:processes' command "ps -u $USER -o pid,stat,%cpu,%mem,cputime,command"
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'

#cdは親ディレクトリからカレントディレクトリを選択しないので表示させないようにする (例: cd ../<TAB>):
#zstyle ':completion:*:cd:*' ignore-parents parent pwd

# オブジェクトファイルとか中間ファイルとかはfileとして補完させない
# zstyle ':completion:*:*files' ignored-patterns '*?.o' '*?~' '*\#'

autoload -Uz compinit && compinit -C -i

# 隠しファイルも補完候補に追加する
_comp_options+=(globdots)

#autoload predict-on
#predict-on

setopt complete_aliases # aliased ls needs if file/dir completions work

# 補完に関するオプション
# http://voidy21.hatenablog.jp/entry/20090902/1251918174
# setopt auto_param_slash      # ディレクトリ名の補完で末尾の / を自動的に付加し、次の補完に備える
setopt mark_dirs             # ファイル名の展開でディレクトリにマッチした場合 末尾に / を付加
setopt list_types            # 補完候補一覧でファイルの種別を識別マーク表示 (訳注:ls -F の記号)
setopt auto_menu             # 補完キー連打で順に補完候補を自動で補完
setopt auto_param_keys       # カッコの対応などを自動的に補完
setopt interactive_comments  # コマンドラインでも # 以降をコメントと見なす
setopt magic_equal_subst     # コマンドラインの引数で --prefix=/usr などの = 以降でも補完できる

setopt complete_in_word      # 語の途中でもカーソル位置で補完
setopt always_last_prompt    # カーソル位置は保持したままファイル名一覧を順次その場で表示

bindkey "^I" menu-complete   # 展開する前に補完候補を出させる(Ctrl-iで補完するようにする)

# npmの補完は重すぎるので無効
compdef -d npm
compdef -d python #-mが重すぎるので無効
compdef -d java
compdef -d man

# http://qiita.com/syui/items/82b080920a4241e96aed
# http://stackoverflow.com/questions/4221239/zsh-use-completions-for-command-x-when-i-type-command-y
compdef '_dispatch git git' g

# エイリアスも補完
setopt no_complete_aliases

# setopt no_unset # 未定義変数の使用禁止

## 自動補完される余分なカンマなどを適宜削除してスムーズに入力できるようにする
# setopt auto_param_keys

