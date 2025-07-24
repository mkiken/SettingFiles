#!/bin/zsh

# https://intellij-support.jetbrains.com/hc/en-us/articles/15268184143890-Shell-Environment-Loading
if [[ $INTELLIJ_ENVIRONMENT_READER ]]; then
  return
fi

# vscodeの判定を変数化
if [[ "$TERM_PROGRAM" == "vscode" ]]; then
  IS_VSCODE=true
else
  IS_VSCODE=false
fi

# Warpの判定を変数化
if [ -z "$IS_WARP" ]; then
  if [[ "$TERM_PROGRAM" == "WarpTerminal" ]]; then
    IS_WARP=true
  else
    IS_WARP=false
  fi
fi
export IS_WARP

if [[ -z "$TMUX" ]] && ! $IS_VSCODE && ! $IS_WARP; then
  tmux new-session -A -s tmux
  return
fi

function zcompile_if_needed() {
    local file="$1"
    if [ ! -f "${file}.zwc" -o "$file" -nt "${file}.zwc" ]; then
        echo "zcompile $file start."
        zcompile "$file"
        # zcompile中のファイルを読み込んでエラーになることがあるようなのでちょっと待つ
        echo "compiling... wait 2 sec."
        sleep 2
        echo "zcompile $file done!"
    fi
}

function source_and_zcompile_if_needed() {
    local file="$1"
    if [[ ! -r "$file" ]]; then
      return 1
    fi
    if ! zcompile_if_needed "$file"; then
      return 1
    fi

    source "$file"
}

source_and_zcompile_if_needed ~/.zshrc_local



REPO="${HOME}/Desktop/repository/"
SET="${REPO}SettingFiles/"
SUBMODULE_DIR="${SET}submodules/"
# MACVIM="/Applications/MacVim.app/Contents/MacOS"
BREW_PREFIX="$(brew --prefix)"
BREW_CASKROOM="$BREW_PREFIX/Caskroom"
BREW_CELLAR="$BREW_PREFIX/Cellar"
EDITOR=nvim

# Exit codes for signal handling
readonly EXIT_CODE_SIGINT=130    # Ctrl+C interruption
readonly EXIT_CODE_SIGPIPE=141   # Broken pipe (e.g., pager termination)

#read Aliases
source_and_zcompile_if_needed "${SET}shell/zsh/alias/main.zsh"

# パスの設定
path=(/usr/local/bin(N-/) $path)
path=($BREW_PREFIX/bin(N-/) $path)

autoload -U colors
colors

# 重複するパスの削除
typeset -U path

# emacsのthemeが読み込める
# http://www.emacswiki.org/emacs/ColorThemeQuestions
export TERM=xterm-256color

export LESS='-R --no-init --RAW-CONTROL-CHARS -M -i'

# https://www.damonde9.com/less%E3%81%A7%E6%96%87%E5%AD%97%E5%8C%96%E3%81%91%E3%81%99%E3%82%8B%E6%99%82%E3%81%AE%E5%AF%BE%E5%BF%9C%E6%96%B9%E6%B3%95/
export LESSCHARSET=utf-8

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

# powerlevel10kのプロンプト設定
source_and_zcompile_if_needed "${SET}shell/zsh/p10k/config.zsh"


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

# コマンドが途中で失敗したら失敗にする
setopt pipefail

## Keybind configuration
bindkey -v

# Read history configuration
source_and_zcompile_if_needed "${SET}shell/zsh/history.zsh"

# Read completion configuration
source_and_zcompile_if_needed "${SET}shell/zsh/completion.zsh"

# http://blog.mkt-sys.jp/2014/06/fix-zsh-env.html
setopt no_flow_control

# 名前で色を付けるようにする
autoload colors
colors

# LS_COLORSを設定しておく
export LS_COLORS='di=34:ln=35:so=32:pi=33:ex=31:bd=46;34:cd=43;34:su=41;30:sg=46;30:tw=42;30:ow=43;30'

# paste:noneでペースト時のハイライトをなくす
# https://github.com/zdharma-continuum/fast-syntax-highlighting/issues/25#issuecomment-1094035433
zle_highlight=(region:standout special:standout suffix:fg=blue,bold isearch:fg=magenta,underline paste:none)

setopt print_eight_bit  #日本語ファイル名等8ビットを通す
setopt extended_glob  # 拡張グロブで補完(~とか^とか。例えばless *.txt~memo.txt ならmemo.txt 以外の *.txt にマッチ)
setopt globdots # 明確なドットの指定なしで.から始まるファイルをマッチ


# 範囲指定できるようにする
# 例 : mkdir {1-3} で フォルダ1, 2, 3を作れる
setopt brace_ccl


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

# コマンドを一時保存する
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
bindkey '^xy' pbcopy-buffer

# http://qiita.com/mollifier/items/7b1cfe609a7911a69706
autoload -Uz edit-command-line
zle -N edit-command-line
bindkey '^v' edit-command-line

#zmv
#http://mollifier.hatenablog.com/entry/20101227/p1
autoload -Uz zmv

bindkey "^xu" undo
bindkey "^xr" redo

# http://mollifier.hatenablog.com/entry/20081214/1229229752
function _kill-backward-blank-word() {
    # 現在位置から左のスペースまでをkillする
    zle set-mark-command
    zle vi-backward-blank-word
    zle kill-region
}
zle -N _kill-backward-blank-word

if ! $IS_WARP; then
  # Warpだとコマンドの入力が無効になることがあるので無効にする
  bindkey '^J' _kill-backward-blank-word
fi


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

source_and_zcompile_if_needed "${SET}shell/zsh/filter/main.zsh"

function filter-bindkey() {
  zle -N select-history
  bindkey '^R' select-history
}

# zsh-vi-modeにkeybindを上書きされないよう、このメソッドで設定
# https://github.com/jeffreytse/zsh-vi-mode/issues/296
function zvm_after_init() {
  filter-bindkey
  bindkey '^D' delete-char-or-list # デフォルトと同じだが、なぜか効かなくなるので再定義
}

# プラグイン設定を読み込み
source_and_zcompile_if_needed "${SET}shell/zsh/plugin.zsh"

# https://github.com/ajeetdsouza/zoxide
eval "$(zoxide init zsh --cmd cd)"

# [Clineが実行したコマンドの結果がCline自身で読み込めない場合の対処法](https://zenn.dev/razokulover/articles/e0e3ae3cbab03d)
if $IS_VSCODE; then
  . "$(code --locate-shell-integration-path zsh)"
fi

# 長時間実行コマンドの通知設定
source_and_zcompile_if_needed "${SET}shell/zsh/notification.zsh"

# 自動コンパイル
# http://blog.n-z.jp/blog/2013-12-10-auto-zshrc-recompile.html
zcompile_if_needed ~/.zshrc