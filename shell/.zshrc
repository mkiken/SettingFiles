# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

REPO="${HOME}/Desktop/repository/"
SET="${REPO}SettingFiles/"
SUBMODULE_DIR="${SET}submodules/"
# MACVIM="/Applications/MacVim.app/Contents/MacOS"
BREW_PREFIX="$(brew --prefix)"
BREW_CASKROOM="$BREW_PREFIX/Caskroom"
BREW_CELLAR="$BREW_PREFIX/Cellar"
FILTER_TOOL='fzf-tmux'
FILTER_COMMAND='${FILTER_TOOL} -d 30% --cycle --exit-0'

#read Aliases
source ~/.aliases


# パスの設定
path=(/usr/local/bin(N-/) $path)
# path=($MACVIM(N-/) $path)

autoload -U colors
colors

# 重複するパスの削除
typeset -U path

# emacsのthemeが読み込める
# http://www.emacswiki.org/emacs/ColorThemeQuestions
export TERM=xterm-256color

export LESS='-R --no-init --RAW-CONTROL-CHARS -M -i'

case "${OSTYPE}" in
  # --------------- Mac(Unix) ---------------
  darwin*)
  # http://please-sleep.cou929.nu/git-completion-and-prompt.html
  if which brew > /dev/null; then
    fpath=($BREW_PREFIX/share/zsh/site-functions(N-/) $fpath)
    # http://d.hatena.ne.jp/sugyan/20130319/1363689394
    # _Z_CMD=j
    # source $BREW_PREFIX/etc/profile.d/z.sh
  else
    fpath=(~/.zsh/completion(N-/) $fpath)
  fi
  path=($HOME/.nodebrew/current/bin(N-/) $path)

esac

# http://qiita.com/Cside_/items/13f85c11d3d0aa35d7ef
# setopt prompt_subst
# autoload -Uz VCS_INFO_get_data_git; VCS_INFO_get_data_git 2> /dev/null

# git stash (fish style)
function fish_style_git_branch {
  local git_branch=$(git current-branch)
    if [ -n "$git_branch" ]; then
      local fish_style_git_branch="${${(M)git_branch:#[/~]}:-${${(@j:/:M)${(@s:/:)git_branch}##.#?}:h}/${git_branch:t}}"
      # ./masterとなるのでmasterにする
      if [[ "$fish_style_git_branch" =~ "^\./.*" ]]; then
        fish_style_git_branch="${fish_style_git_branch#./}"
      fi
      echo $fish_style_git_branch
    fi
}

# git stash count
function git_prompt_stash_count {
  local COUNT=$(git stash list 2>/dev/null | wc -l | tr -d ' ')
  if [ "$COUNT" -gt 0 ]; then
    echo "($COUNT)"
  fi
}

function my-git-status {
	# http://stackoverflow.com/questions/15715825/how-do-you-get-git-repos-name-in-some-git-repository
	local tmp_path=$(git rev-parse --show-toplevel 2>/dev/null)
	if [ -n "$tmp_path" ]; then
		local repo_name=`basename $tmp_path`
		echo "[%F{yellow}${repo_name}%f:%F{magenta}$(fish_style_git_branch)%f$(git_prompt_stash_count)]"
	fi

}

# powerlevel10kのプロンプト設定

source $BREW_PREFIX/opt/powerlevel10k/powerlevel10k.zsh-theme

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh


# 今のshellの履歴数
function my_history_count {
  echo '%i'
}
POWERLEVEL9K_CUSTOM_MY_HISTORY_COUNT="my_history_count"
POWERLEVEL9K_CUSTOM_MY_HISTORY_COUNT_BACKGROUND="grey50"
POWERLEVEL9K_CUSTOM_MY_HISTORY_COUNT_FOREGROUND="$DEFAULT_COLOR"

# レポジトリ名
function get_git_repo_name {
	# http://stackoverflow.com/questions/15715825/how-do-you-get-git-repos-name-in-some-git-repository
	local tmp_path=$(git rev-parse --show-toplevel 2>/dev/null)
	if [ -n "$tmp_path" ]; then
		echo `basename $tmp_path`
	fi
}
POWERLEVEL9K_CUSTOM_GIT_REPO_NAME="get_git_repo_name"
POWERLEVEL9K_CUSTOM_GIT_REPO_NAME_BACKGROUND="green"
# POWERLEVEL9K_CUSTOM_GIT_REPO_NAME_FOREGROUND="$DEFAULT_COLOR"

# ブランチ名
function get_git_branch_name {
	local tmp_path=$(git rev-parse --show-toplevel 2>/dev/null)
	if [ -n "$tmp_path" ]; then
	  local tmp_name=`fish_style_git_branch`
	  if [ -n "$tmp_name" ]; then
		  echo "${tmp_name}`git_prompt_stash_count`"
	  fi
	fi
}
POWERLEVEL9K_CUSTOM_GIT_BRANCH_NAME="get_git_branch_name"
POWERLEVEL9K_CUSTOM_GIT_BRANCH_NAME_BACKGROUND="yellow"
# POWERLEVEL9K_CUSTOM_GIT_BRANCH_NAME_FOREGROUND="$DEFAULT_COLOR"

# ranger subshell count
# https://github-wiki-see.page/m/gokcehan/lf/wiki/Tips
function prompt_ranger_subshell_count() {
    # p10k segment -f 208 -i '📂' -t "$RANGER_LEVEL" -c "$RANGER_LEVEL"
    p10k segment -f 208 -b 207 -i '📂' -t "" -c "$RANGER_LEVEL"
  }

POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(dir custom_git_repo_name custom_git_branch_name ranger_subshell_count)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status command_execution_time background_jobs custom_my_history_count time)
#
POWERLEVEL9K_SHORTEN_DIR_LENGTH=1
POWERLEVEL9K_SHORTEN_DELIMITER=""
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_from_right"

# POWERLEVEL9K_VCS_GIT_HOOKS=(vcs-detect-changes git-untracked git-aheadbehind git-stash git-remotebranch git-tagname)
# POWERLEVEL9K_VCS_GIT_HOOKS=(git-stash)
# POWERLEVEL9K_VCS_SHOW_SUBMODULE_DIRTY=false

#from http://news.mynavi.jp/column/zsh/index.html
# case ${UID} in
	# 0) #for super user
		# RPROMPT='[%F{yellow}%D{%T}%f]'
		# ;;
	# *)
    # RPROMPT='[%F{blue}%D{%T}%f]'
# esac

function precmd_prompt () {
  # https://github.com/sorin-ionescu/prezto/issues/290
  local pwd="${PWD/#$HOME/~}"
  local fish_style_pwd="${${(M)pwd:#[/~]}:-${${(@j:/:M)${(@s:/:)pwd}##.#?}:h}/${pwd:t}}"
  PROMPT="%{%(?.$fg[green].$fg[red])%}%U$fish_style_pwd%u%{$reset_color%} $(my-git-status) %{$fg[cyan]%}%i%{$reset_color%} %{%}%#%{%}%(1j.%j.) "
  # PROMPT="%{%(?.$fg[green].$fg[red])%}%n%{$reset_color%} [%F{cyan}%(5~,%-2~/../%2~,%~)%f] %{%}%#%{%}%(1j.%j.) "
}
# precmd_functions=(precmd_prompt)

# http://qiita.com/yuyuchu3333/items/b10542db482c3ac8b059
function chpwd() { pwd;ls_abbrev }

function ls_abbrev() {
    if [[ ! -r $PWD ]]; then
        return
    fi
    # -a : Do not ignore entries starting with ..
    # -C : Force multi-column output.
    # -F : Append indicator (one of */=>@|) to entries.
    local cmd_ls='ls'
    local -a opt_ls
    opt_ls=('-aCF' '--color=always')
    case "${OSTYPE}" in
        freebsd*|darwin*)
            if type gls > /dev/null 2>&1; then
                cmd_ls='gls'
            else
                # -G : Enable colorized output.
                opt_ls=('-aCFG')
            fi
            ;;
    esac

    local ls_result
    ls_result=$(CLICOLOR_FORCE=1 COLUMNS=$COLUMNS command $cmd_ls ${opt_ls[@]} | sed $'/^\e\[[0-9;]*m$/d')

    local ls_lines=$(echo "$ls_result" | wc -l | tr -d ' ')

    if [ $ls_lines -gt 10 ]; then
        echo "$ls_result" | head -n 5
        echo '...'
        echo "$ls_result" | tail -n 5
        echo "$(command ls -1 -A | wc -l | tr -d ' ') files exist"
    else
        echo "$ls_result"
    fi
}

# http://qiita.com/takc923/items/be459e2962aa11e33d12
function command_not_found_handler() {
    if [ $# != 1 ]; then
        return 127
    # elif [ -d $0 ]; then
        # ls -la $0
        # return 0
    elif  [ -f $0 ]; then
        less $0
        return 0
    else
        return 127
    fi
}

# http://hagetak.hatenablog.com/entry/2014/07/17/093750
function mkcd(){
  mkdir $1 && cd $1
}

# auto directory pushd that you can get dirs list by cd -[tab]
setopt auto_cd # ディレクトリ名と一致した場合 cd
setopt auto_pushd
setopt pushd_ignore_dups # 同じディレクトリは追加しない

# command correct edition before each completion attempt
setopt correct

# GLOBDOTS lets files beginning with a . be matched without explicitly specifying the dot.
setopt globdots

# compacked complete list display
setopt list_packed

# no remove postfix slash of command line
unsetopt auto_param_slash      # ディレクトリ名の補完で末尾の / を自動的に付加し、次の補完に備える

# no beep sound when complete list displayed
setopt nolistbeep

# ビープ音を鳴らさないようにする
setopt NO_beep

## Keybind configuration
# emacs like keybind (e.x. Ctrl-a goes to head of a line and Ctrl-e goes to end of it)
bindkey -e

# historical backward/forward search with linehead string binded to ^P/^N
autoload history-search-end
zle -N history-beginning-search-backward-end history-search-end
zle -N history-beginning-search-forward-end history-search-end
bindkey "^P" history-beginning-search-backward-end
bindkey "^N" history-beginning-search-forward-end

## Command history configuration
#
export HISTFILE=$HOME/.zsh_history
export HISTSIZE=100000        # メモリ上の履歴リストに保存されるイベントの最大数
export SAVEHIST=100000        # 履歴ファイルに保存されるイベントの最大数

setopt hist_expire_dups_first # 履歴を切り詰める際に、重複する最も古いイベントから消す
setopt hist_ignore_all_dups   # 履歴が重複した場合に古い履歴を削除する
setopt hist_ignore_dups       # 前回のイベントと重複する場合、履歴に保存しない
setopt hist_save_no_dups      # 履歴ファイルに書き出す際、新しいコマンドと重複する古いコマンドは切り捨てる
setopt share_history          # 全てのセッションで履歴を共有する

## Completion configuration
#http://qiita.com/items/f2971728c845c75e9967
autoload -U compinit -u && compinit -u
compinit -u

# 隠しファイルも補完候補に追加する
_comp_options+=(globdots)

#autoload predict-on
#predict-on

setopt complete_aliases # aliased ls needs if file/dir completions work

# http://blog.mkt-sys.jp/2014/06/fix-zsh-env.html
setopt no_flow_control

#from http://qiita.com/items/ed2d36698a5cc314557d
zstyle ':completion:*:default' menu select=2
zstyle ':completion:*' verbose yes
# zstyle ':completion:*' completer _expand _complete _match _prefix _approximate _list _history
zstyle ':completion:*:messages' format '%F{YELLOW}%d'$DEFAULT
zstyle ':completion:*:warnings' format '%F{RED}No matches for:''%F{YELLOW} %d'$DEFAULT
zstyle ':completion:*:descriptions' format '%F{YELLOW}completing %B%d%b'$DEFAULT
zstyle ':completion:*:options' description 'yes'
zstyle ':completion:*:descriptions' format '%F{yellow}Completing %B%d%b%f'$DEFAULT

# マッチ種別を別々に表示
zstyle ':completion:*' group-name ''

# セパレータを設定する
zstyle ':completion:*' list-separator '-->'
zstyle ':completion:*:manuals' separate-sections true

# 補完機能で大文字小文字を区別しないよう(case insensitive)にする
#http://nukesaq88.hatenablog.com/entry/2013/04/18/183335
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# 名前で色を付けるようにする
autoload colors
colors

# LS_COLORSを設定しておく
export LS_COLORS='di=34:ln=35:so=32:pi=33:ex=31:bd=46;34:cd=43;34:su=41;30:sg=46;30:tw=42;30:ow=43;30'

# http://www.spookies.co.jp/blog/zsh-5-0-0-%E3%81%AE%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%83%A9%E3%82%A4%E3%83%B3%E3%83%8F%E3%82%A4%E3%83%A9%E3%82%A4%E3%83%88%E3%82%92%E4%BD%BF%E3%81%86
zle_highlight=(region:standout special:standout suffix:fg=blue,bold isearch:fg=magenta,underline)

# ファイル補完候補に色を付ける
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}

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

setopt print_eight_bit  #日本語ファイル名等8ビットを通す
setopt extended_glob  # 拡張グロブで補完(~とか^とか。例えばless *.txt~memo.txt ならmemo.txt 以外の *.txt にマッチ)
setopt globdots # 明確なドットの指定なしで.から始まるファイルをマッチ

bindkey "^I" menu-complete   # 展開する前に補完候補を出させる(Ctrl-iで補完するようにする)

# 範囲指定できるようにする
# 例 : mkdir {1-3} で フォルダ1, 2, 3を作れる
setopt brace_ccl

# manの補完をセクション番号別に表示させる
zstyle ':completion:*:manuals' separate-sections true

# 変数の添字を補完する
zstyle ':completion:*:*:-subscript-:*' tag-order indexes parameters


#cdは親ディレクトリからカレントディレクトリを選択しないので表示させないようにする (例: cd ../<TAB>):
#zstyle ':completion:*:cd:*' ignore-parents parent pwd

# オブジェクトファイルとか中間ファイルとかはfileとして補完させない
# zstyle ':completion:*:*files' ignored-patterns '*?.o' '*?~' '*\#'

## 辞書順ではなく数字順に並べる
setopt numeric_glob_sort

## 実行したプロセスの消費時間が5秒以上かかったら
## 自動的に消費時間の統計情報を表示する
REPORTTIME=5

## ^Dでログアウトしないようにする
setopt ignore_eof

## 「/」も単語区切りとみなす
# WORDCHARS=${WORDCHARS:s,/,,}
WORDCHARS='*?[]~&!#$%^(){}<>'

# http://mba-hack.blogspot.jp/2012/11/zsh.html
show_buffer_stack() {
  POSTDISPLAY="
stack: $LBUFFER"
  zle push-line-or-edit
}
zle -N show_buffer_stack
setopt noflowcontrol
bindkey '^Q' show_buffer_stack

pbcopy-buffer(){
    print -rn $BUFFER | pbcopy
    zle -M "pbcopy: ${BUFFER}"
}

zle -N pbcopy-buffer
bindkey '^xp' pbcopy-buffer

# http://qiita.com/yoshikaw/items/fe4aca1110979e223f7e
bindkey '^]'   vi-find-next-char
bindkey '^[^]' vi-find-prev-char

# http://qiita.com/mollifier/items/7b1cfe609a7911a69706
autoload -Uz edit-command-line
zle -N edit-command-line
bindkey '^xe' edit-command-line

# http://qiita.com/mollifier/items/33bda290fe3c0ae7b3bb
zstyle ':completion:*:processes' command "ps -u $USER -o pid,stat,%cpu,%mem,cputime,command"

# http://qiita.com/items/55651f44f91123f1881c
# url: $1, delimiter: $2, prefix: $3, words: $4..
function web_search {
	local url=$1       && shift
	local delimiter=$1 && shift
	local prefix=$1    && shift
	local query

	while [ -n "$1" ]; do
		if [ -n "$query" ]; then
			query="${query}${delimiter}${prefix}$1"
		else
			query="${prefix}$1"
		fi
		shift
	done

	open "${url}${query}"
}

function google () {
	web_search "https://www.google.co.jp/search?&q=" "+" "" $*
}

#zmv
#http://mollifier.hatenablog.com/entry/20101227/p1
autoload -Uz zmv

# http://qiita.com/mollifier/items/9258c8fd8b59894b1bcd
bindkey '^J' self-insert

# http://mollifier.hatenablog.com/entry/20081210/1228917616
# http://mollifier.hatenablog.com/entry/20090414/1239634907
autoload smart-insert-last-word
zle -N insert-last-word smart-insert-last-word
bindkey '^O' insert-last-word

#http://qiita.com/items/156464de9caf64338b17
bindkey "^[u" undo
bindkey "^[r" redo
# bindkey "^?" redo

# altで単語移動
# http://superuser.com/questions/301029/problem-with-ctrl-left-right-bindings-in-oh-my-zsh
bindkey "[C" emacs-forward-word   #control left
bindkey "[D" emacs-backward-word        #control right

# http://mollifier.hatenablog.com/entry/20081214/1229229752
function _kill-backward-blank-word() {
    # 現在位置から左のスペースまでをkillする
    zle set-mark-command
    zle vi-backward-blank-word
    zle kill-region
}
zle -N _kill-backward-blank-word
bindkey '^J' _kill-backward-blank-word

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

# http://kaworu.jpn.org/kaworu/2012-05-02-1.php
export MANPAGER='less -R'
man() {
	env \
		LESS_TERMCAP_mb=$(printf "\e[1;31m") \
		LESS_TERMCAP_md=$(printf "\e[1;31m") \
		LESS_TERMCAP_me=$(printf "\e[0m") \
		LESS_TERMCAP_se=$(printf "\e[0m") \
		LESS_TERMCAP_so=$(printf "\e[1;44;33m") \
		LESS_TERMCAP_ue=$(printf "\e[0m") \
		LESS_TERMCAP_us=$(printf "\e[1;32m") \
		man "$@"
}

function exists { which $1 &> /dev/null }

if exists ${FILTER_TOOL}; then
  source "${SET}shell/.zshrc_filter"
fi

# if exists fzf; then
#   source "${SET}.zshrc_fzf"
#   export FZF_DEFAULT_OPTS="--extended --cycle --reverse --no-sort --multi"
#   [ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
# fi

# zle -N zle-keymap-select auto-fu-zle-keymap-select
if [ -f ${SUBMODULE_DIR}zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]; then
  source ${SUBMODULE_DIR}zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

source ${SUBMODULE_DIR}zsh-bd/bd.zsh

source ${SUBMODULE_DIR}zaw/zaw.zsh
# zstyle ':filter-select:highlight' selected fg=black,bg=white,standout
zstyle ':filter-select:highlight' matched fg=yellow,standout
zstyle ':filter-select' max-lines 20 # use 10 lines for filter-select
zstyle ':filter-select' rotate-list yes # enable rotation for filter-select
zstyle ':filter-select' case-insensitive yes # enable case-insensitive search
zstyle ':filter-select' extended-search yes # see below
zstyle ':filter-select' hist-find-no-dups yes # ignore duplicates in history source

function zaw-src-gitdir () {
  _dir=$(git rev-parse --show-cdup 2>/dev/null)
  if [ $? -eq 0 ]
  then
    candidates=( $(git ls-files ${_dir} | perl -MFile::Basename -nle \
                                               '$a{dirname $_}++; END{delete $a{"."}; print for sort keys %a}') )
  fi
  actions=("zaw-src-gitdir-cd")
  act_descriptions=("change directory in git repos")
}

function zaw-src-gitdir-cd () {
  BUFFER="cd $1"
  zle accept-line
}
zaw-register-src -n gitdir zaw-src-gitdir

# bindkey '^R' zaw-history
bindkey '^R' select-history
bindkey '^X^F' zaw-git-files
bindkey '^X^B' zaw-git-branches
bindkey '^X^S' zaw-ssh-hosts
bindkey '^X^P' zaw-process
bindkey '^X^T' zaw-tmux
bindkey '^X^A' zaw-applications
bindkey '^X^O' zaw-open-file
# bindkey '^X?'  zaw-print-src

# http://qiita.com/scalper/items/4728afaac9962bf91bfa
# bindkey '^X^X' zaw-cdr
bindkey '^X^D' zaw-gitdir

if [ -z "$LOAD_COMPLETE" ]; then
  # 再読み込みすると落ちるので1回のみロード
  source ${SUBMODULE_DIR}/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

# 自動コンパイル
# http://blog.n-z.jp/blog/2013-12-10-auto-zshrc-recompile.html
if [ ! -f ~/.zshrc.zwc -o ~/.zshrc -nt ~/.zshrc.zwc ]; then
   zcompile ~/.zshrc
fi

LOAD_COMPLETE=`date`
