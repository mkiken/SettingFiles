#read Aliases
source ~/.aliases


# パスの設定
PATH=/usr/local/bin:$PATH

autoload -U colors
colors

# 重複するパスの削除
typeset -U path

# emacsのthemeが読み込める
# http://www.emacswiki.org/emacs/ColorThemeQuestions
export TERM=xterm-256color

# http://qiita.com/Cside_/items/13f85c11d3d0aa35d7ef
setopt prompt_subst
autoload -Uz VCS_INFO_get_data_git; VCS_INFO_get_data_git 2> /dev/null

# git stash count
function git_prompt_stash_count {
  local COUNT=$(git stash list 2>/dev/null | wc -l | tr -d ' ')
  if [ "$COUNT" -gt 0 ]; then
    echo "($COUNT)"
  fi
}

# export LC_CTYPE=ja_JP.UTF-8
# export LANG=ja_JP.UTF-8

# export LC_CTYPE=UTF-8
# export LANG=UTF-8

# function rprompt-git-current-branch {
  # local name st color gitdir action
  # # if [[ "$PWD" =~ '/¥.git(/.*)?$' ]]; then
    # # return
  # # fi
  # name=$(basename "`git symbolic-ref HEAD 2> /dev/null`")
  # if [[ -z $name ]]; then
    # return
  # fi

  # gitdir=`git rev-parse --git-dir 2> /dev/null`
  # action=`VCS_INFO_git_getaction "$gitdir"` && action="($action)"

  # st=`git status 2> /dev/null`
  # if [[ -n `echo "$st" | grep "^nothing to"` ]]; then
    # color=%F{green}
  # elif [[ -n `echo "$st" | grep "^nothing added"` ]]; then
    # color=%F{yellow}
  # elif [[ -n `echo "$st" | grep "^# Untracked"` ]]; then
    # color=%B%F{red}
  # else
     # color=%F{red}
  # fi
  # echo "::$color$name`git_prompt_stash_count`$action%f%b"
# }

# http://smokycat.info/zsh/262
# function prompt-git-current-branch {
        # local name st color
        # name=`git symbolic-ref HEAD 2> /dev/null`
        # if [[ -z $name ]]
        # then
                # return
        # fi
        # name=`basename $name`

        # st=`git status`
        # if [[ -n `echo $st | grep "^nothing to"` ]]
        # then
                # color="green"
        # else
                # color="red"
        # fi

        # echo "%F{$color}[$name]%f"
# }

# -------------- 使い方 ---------------- #
# RPROMPT=''

source "${SET}/submodules/zsh-git-prompt/zshrc.sh"
export __GIT_PROMPT_DIR="${SET}/submodules/zsh-git-prompt"

#from http://news.mynavi.jp/column/zsh/index.html
case ${UID} in
	0) #for super user
		# RPROMPT='(%~)'
		# PROMPT=$'%B%m%b:%?:%# '
		# RPROMPT='(%F{yellow}%(5~,%-2~/../%2~,%~)%f)`rprompt-git-current-branch`'
		RPROMPT='[%F{yellow}%(5~,%-2~/../%2~,%~)%f]$(git_super_status)`git_prompt_stash_count`'
		#PROMPT=$'%m: %n %D{%T} %{%}%#%{%} '
		PROMPT="%{$fg[green]%} %n: %D{%T} %{%}%#%{%}%{$reset_color%} "
		;;
	*)
    # RPROMPT='(%F{cyan}%(5~,%-2~/../%2~,%~)%f)`rprompt-git-current-branch`'
    RPROMPT='[%F{cyan}%(5~,%-2~/../%2~,%~)%f]$(git_super_status)`git_prompt_stash_count`'
    # RPROMPT='(%F{cyan}%(5~,%-2~/../%2~,%~)%f)`prompt-git-current-branch`'
		# RPROMPT='(%F{cyan}%(5~,%-2~/../%2~,%~)%f)'
		#PROMPT=$'%m: %n %D{%T} %{%}%#%{%} '
		PROMPT="%{$fg[green]%} %n: %D{%T} %{%}%#%{%}%{$reset_color%} "
esac

function precmd_prompt () {
	PROMPT="%{%(?.$fg[green].$fg[red])%}%n[%D{%T}] %{%}%#%{%}%{$reset_color%} "
}
precmd_functions=(precmd_prompt)

#SPROMPT="%r is correct? [n,y,a,e]:] "
#http://0xcc.net/blog/archives/000032.html
# PROMPT='%n@%m:%(5~,%-2~/../%2~,%~)%# '



# http://qiita.com/yuyuchu3333/items/b10542db482c3ac8b059
function chpwd() { ls_abbrev }

ls_abbrev() {
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

# compacked complete list display
setopt list_packed

# no remove postfix slash of command line
# setopt noautoremoveslash
# unsetopt autoremoveslash
unsetopt auto_param_slash      # ディレクトリ名の補完で末尾の / を自動的に付加し、次の補完に備える
# unsetopt

# no beep sound when complete list displayed
#
setopt nolistbeep

# # stop the beep
# #
# set bell-style none

# # never beep when complete
# #
# set matchbeep=never

# # stop the beep
# #
# set nobeep

# ビープ音を鳴らさないようにする
setopt NO_beep

## Keybind configuration
# emacs like keybind (e.x. Ctrl-a goes to head of a line and Ctrl-e goes
#   to end of it)
bindkey -e

# historical backward/forward search with linehead string binded to ^P/^N
autoload history-search-end
zle -N history-beginning-search-backward-end history-search-end
zle -N history-beginning-search-forward-end history-search-end
bindkey "^P" history-beginning-search-backward-end
bindkey "^N" history-beginning-search-forward-end

## Command history configuration
#
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt hist_ignore_dups     # ignore duplication command history list
setopt share_history        # share command history data

## Completion configuration
#http://qiita.com/items/f2971728c845c75e9967
autoload -U compinit && compinit
compinit

#autoload predict-on
#predict-on

setopt complete_aliases # aliased ls needs if file/dir completions work



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

# ファイル補完候補に色を付ける
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}

#grepの結果に色を付ける
#http://d.hatena.ne.jp/bubbles/20081210/1228918665
export GREP_OPTIONS='--color=always'

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
alias zmv='noglob zmv -W'
alias zcp='zmv -C'

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

#incremental-complete
#autoload incremental-complete-word
#zle -N incremental-complete-word
#bindkey '\C-xI' incremental-complete-word


: << '#_comment_out'

# Incremental completion for zsh
# by y.fujii <y-fujii at mimosa-pudica.net>, public domain

#autoload -U compinit
zle -N self-insert self-insert-incr
zle -N vi-cmd-mode-incr
zle -N vi-backward-delete-char-incr
zle -N backward-delete-char-incr
zle -N expand-or-complete-prefix-incr
#compinit

bindkey -M viins '^[' vi-cmd-mode-incr
bindkey -M viins '^h' vi-backward-delete-char-incr
bindkey -M viins '^?' vi-backward-delete-char-incr
bindkey -M viins '^i' expand-or-complete-prefix-incr
bindkey -M emacs '^h' backward-delete-char-incr
bindkey -M emacs '^?' backward-delete-char-incr
bindkey -M emacs '^i' expand-or-complete-prefix-incr

setopt automenu

now_predict=0
glob_context=0

function limit-completion
{
    # echo "limit-completetion"
	if ((compstate[nmatches] <= 1)); then
		zle -M ""
	elif ((compstate[list_lines] > 6)); then
		compstate[list]=""
		zle -M "$compstate[nmatches] matches($compstate[list_lines] lines). expand?"
		# zle -M "$compstate[nmatches]"
	fi
}

function correct-prediction
{
    # echo "correct-prediction"
	if ((now_predict == 1)); then
		if [[ "$BUFFER" != "$buffer_prd" ]] || ((CURSOR != cursor_org)); then
			now_predict=0
		fi
	fi
}

function remove-prediction
{
    # echo "remove-prediction"
	if ((now_predict == 1)); then
		BUFFER="$buffer_org"
		now_predict=0
	fi
}

function show-prediction
{
    # echo "show-prediction"
	# assert(now_predict == 0)
	# *, ^のときは補完ではなく，list-expandしてほしい
	if
		((PENDING == 0)) &&
		((CURSOR > 1)) &&
		[[ "$PREBUFFER" == "" ]] &&
		(
		[[ "$BUFFER[CURSOR]" == "*" ]] ||
			[[ "$BUFFER[CURSOR]" == "^" ]]
		)
	then
		glob_context=1
		zle list-expand
	elif
		((PENDING == 0)) &&
		((CURSOR > 1)) &&
		[[ "$PREBUFFER" == "" ]] &&
		[[ "$BUFFER[CURSOR]" != " " ]]
	then
    # echo "show-prediction3"
		cursor_org="$CURSOR"
		buffer_org="$BUFFER"
		comppostfuncs=(limit-completion)
		if ((glob_context == 0))
		then
			zle complete-word
		else
			# glob文脈だったらcomplete-wordでなく，list-expandを呼ぶ
			zle list-expand
		fi
		# zle complete-word
    # echo "show-prediction2"
		cursor_prd="$CURSOR"
		buffer_prd="$BUFFER"
		if [[ "$buffer_org[1,cursor_org]" == "$buffer_prd[1,cursor_org]" ]]; then
    # echo "show-prediction4"
			CURSOR="$cursor_org"
			if [[ "$buffer_org" != "$buffer_prd" ]] || ((cursor_org != cursor_prd)); then
				now_predict=1
			fi
		else
    # echo "show-prediction5"
            BUFFER="$buffer_org"
            # BUFFER="$buffer_prd"
            CURSOR="$cursor_org"
		fi
		echo -n "\e[32m"
	else
		glob_context=0
		zle -M ""
	fi
}

function preexec
{
	echo -n "\e[39m"
}

function vi-cmd-mode-incr
{
	correct-prediction
	remove-prediction
	zle vi-cmd-mode
}

function self-insert-incr
{
	correct-prediction
	remove-prediction
	if zle .self-insert; then
		show-prediction
	fi
}

function vi-backward-delete-char-incr
{
	correct-prediction
	remove-prediction
	if zle vi-backward-delete-char; then
		show-prediction
	fi
}

function backward-delete-char-incr
{
	correct-prediction
	remove-prediction
	if zle backward-delete-char; then
		show-prediction
	fi
}

function expand-or-complete-prefix-incr
{
	correct-prediction
	if ((now_predict == 1)); then
		CURSOR="$cursor_prd"
		now_predict=0
		comppostfuncs=(limit-completion)
		zle list-choices
	else
		remove-prediction
		zle expand-or-complete-prefix
	fi
}
#_comment_out

#=============================
# source auto-fu.zsh
#=============================
if [ -f "${SET}/submodules/auto-fu.zsh/auto-fu.zsh" ]; then
# if [ -f ~/.zsh/auto-fu.zsh ]; then
    source ~/.zsh/auto-fu.zsh
    function zle-line-init () {
        auto-fu-init
    }
    zle -N zle-line-init
    # zstyle ':completion:*' completer _oldlist _complete
    zstyle ':completion:*' completer _oldlist _expand _complete _match _prefix _approximate _list _history
    zstyle ':auto-fu:highlight' completion/one fg=black
fi
# 「-azfu-」を表示させない
zstyle ':auto-fu:var' postdisplay $''



# npmの補完は重すぎるので無効
compdef -d npm
compdef -d python #-mが重すぎるので無効


# http://qiita.com/syui/items/82b080920a4241e96aed
# http://stackoverflow.com/questions/4221239/zsh-use-completions-for-command-x-when-i-type-command-y
compdef '_dispatch git git' g

  # エイリアスも補完
setopt no_complete_aliases


case "${OSTYPE}" in
  # --------------- Mac(Unix) ---------------
  darwin*)
  # http://please-sleep.cou929.nu/git-completion-and-prompt.html
  if which brew > /dev/null; then
    fpath=($(brew --prefix)/share/zsh/site-functions $fpath)
  else
    fpath=(~/.zsh/completion $fpath)
  fi

  export PATH=$HOME/.nodebrew/current/bin:$PATH

  # http://d.hatena.ne.jp/sugyan/20130319/1363689394
  if which brew > /dev/null; then
    _Z_CMD=j
    source $(brew --prefix)/etc/profile.d/z.sh
  fi
  ;;
esac


