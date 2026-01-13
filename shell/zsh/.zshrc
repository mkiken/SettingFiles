#!/bin/zsh

# vscodeの判定を変数化
if [[ "$TERM_PROGRAM" == "vscode" ]]; then
  IS_VSCODE=true
else
  IS_VSCODE=false
fi

if [[ "$TERM_PROGRAM" == "kiro" ]]; then
  IS_KIRO=true
else
  IS_KIRO=false
fi

# IDEの判定を統合（IntelliJまたはVSCodeの場合true）
if [[ $JETBRAINS_INTELLIJ_ZSH_DIR ]] || $IS_VSCODE || $IS_KIRO; then
  IS_IDE=true
else
  IS_IDE=false
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

if [[ -z "$TMUX" ]] && ! $IS_IDE && ! $IS_WARP; then
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

readonly REPO="${HOME}/Desktop/repository/"
readonly SET="${REPO}SettingFiles/"
readonly SUBMODULE_DIR="${SET}submodules/"
# MACVIM="/Applications/MacVim.app/Contents/MacOS"
if command -v brew >/dev/null 2>&1; then
  readonly BREW_PREFIX="$(brew --prefix)"
  readonly BREW_CASKROOM="$BREW_PREFIX/Caskroom"
  readonly BREW_CELLAR="$BREW_PREFIX/Cellar"
fi
export EDITOR=nvim

# Exit codes for signal handling
[[ -z "${EXIT_CODE_SIGINT:-}" ]] && readonly EXIT_CODE_SIGINT=130    # Ctrl+C interruption
[[ -z "${EXIT_CODE_SIGPIPE:-}" ]] && readonly EXIT_CODE_SIGPIPE=141   # Broken pipe (e.g., pager termination)

#read Aliases
source_and_zcompile_if_needed "${SET}shell/zsh/alias/main.zsh" || echo "Warning: Failed to load aliases" >&2

# パスの設定
path=(/usr/local/bin(N-/) $path)
path=($BREW_PREFIX/bin(N-/) $path)
path=($HOME/.local/bin(N-/) $path) # pipxのパス

# 名前で色を付けるようにする
autoload -U colors
colors

# 重複するパスの削除
typeset -U path

# emacsのthemeが読み込める
# http://www.emacswiki.org/emacs/ColorThemeQuestions
# TERMが未設定またはdumbの場合のみ設定
[[ -z "$TERM" || "$TERM" == "dumb" ]] && export TERM=xterm-256color

export LESS='-R --no-init --RAW-CONTROL-CHARS -M -i'

# https://www.damonde9.com/less%E3%81%A7%E6%96%87%E5%AD%97%E5%8C%96%E3%81%91%E3%81%99%E3%82%8B%E6%99%82%E3%81%AE%E5%AF%BE%E5%BF%9C%E6%96%B9%E6%B3%95/
export LESSCHARSET=utf-8

case "${OSTYPE}" in
  # --------------- Mac(Unix) ---------------
  darwin*)
  # http://please-sleep.cou929.nu/git-completion-and-prompt.html
  if which brew > /dev/null; then
    fpath=($BREW_PREFIX/share/zsh/site-functions(N-/) $fpath)
  else
    fpath=(~/.zsh/completion(N-/) $fpath)
  fi

esac

# Cursorでコマンドが止まる問題の対応
# [Cursor agent mode - when running terminal commands often hangs up the terminal, requiring a click to pop it out in order to continue commands - Bug Reports - Cursor - Community Forum](https://forum.cursor.com/t/cursor-agent-mode-when-running-terminal-commands-often-hangs-up-the-terminal-requiring-a-click-to-pop-it-out-in-order-to-continue-commands/59969/16)
if [[ -n "$CURSOR_AGENT" ]] || $IS_KIRO; then
  # 互換性向上のためテーマ初期化をスキップ
else
  # powerlevel10kのプロンプト設定
  source_and_zcompile_if_needed "${SET}shell/zsh/p10k/config.zsh" || echo "Warning: Failed to load powerlevel10k config" >&2
fi


# http://qiita.com/yuyuchu3333/items/b10542db482c3ac8b059
function chpwd() { pwd;ls_abbrev }

function ls_abbrev() {
    [[ ! -r $PWD ]] && return 0

    # ezaが使える場合は使用、なければ従来のls
    if command -v eza >/dev/null 2>&1; then
        local ls_result="$(eza -a --color=always --grid 2>/dev/null)"
    else
        local ls_result="$(ls -ACF --color=always 2>/dev/null || ls -ACFG 2>/dev/null)"
    fi

    local ls_lines=$(echo "$ls_result" | wc -l)
    if [[ $ls_lines -gt 10 ]]; then
        echo "$ls_result" | head -5
        echo '...'
        echo "$ls_result" | tail -5
        echo "$ls_lines files exist"
    else
        echo "$ls_result"
    fi
}

# http://hagetak.hatenablog.com/entry/2014/07/17/093750
function mkcd(){
  mkdir -p "$1" && cd "$1" || return 1
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
source_and_zcompile_if_needed "${SET}shell/zsh/history.zsh" || echo "Warning: Failed to load history config" >&2

# Read completion configuration
source_and_zcompile_if_needed "${SET}shell/zsh/completion.zsh" || echo "Warning: Failed to load completion config" >&2

# http://blog.mkt-sys.jp/2014/06/fix-zsh-env.html
setopt no_flow_control

# LS_COLORSを設定しておく
export LS_COLORS='di=34:ln=35:so=32:pi=33:ex=31:bd=46;34:cd=43;34:su=41;30:sg=46;30:tw=42;30:ow=43;30'

# paste:noneでペースト時のハイライトをなくす
# https://github.com/zdharma-continuum/fast-syntax-highlighting/issues/25#issuecomment-1094035433
zle_highlight=(region:standout special:standout suffix:fg=blue,bold isearch:fg=magenta,underline paste:none)

setopt print_eight_bit  #日本語ファイル名等8ビットを通す
setopt extended_glob  # 拡張グロブで補完(~とか^とか。例えばless *.txt~memo.txt ならmemo.txt 以外の *.txt にマッチ)

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

## globでマッチしなかった場合にエラーにしない
## [zsh: no matches found: #Zsh - Qiita](https://qiita.com/ponsuke0531/items/8dd9ba566a13edc03fe2)
setopt nonomatch

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
bindkey '^xe' edit-command-line

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
	no_notify env \
		LESS_TERMCAP_mb=$(printf "\e[1;31m") \
		LESS_TERMCAP_md=$(printf "\e[1;31m") \
		LESS_TERMCAP_me=$(printf "\e[0m") \
		LESS_TERMCAP_se=$(printf "\e[0m") \
		LESS_TERMCAP_so=$(printf "\e[1;44;33m") \
		LESS_TERMCAP_ue=$(printf "\e[0m") \
		LESS_TERMCAP_us=$(printf "\e[1;32m") \
		man "$@"
}

source_and_zcompile_if_needed "${SET}shell/zsh/filter/main.zsh" || echo "Warning: Failed to load filter config" >&2

function filter-bindkey() {
  zle -N select-history
  bindkey '^R' select-history
}

# zsh-vi-modeにkeybindを上書きされないよう、このメソッドで設定
# https://github.com/jeffreytse/zsh-vi-mode/issues/296
function zvm_after_init() {
  filter-bindkey
  bindkey '^D' delete-char-or-list # デフォルトと同じだが、なぜか効かなくなるので再定義
  # 履歴の行頭マッチ検索を有効化
  bindkey '^P' history-beginning-search-backward
  bindkey '^N' history-beginning-search-forward
}

# プラグイン設定を読み込み
source_and_zcompile_if_needed "${SET}shell/zsh/plugin.zsh" || echo "Warning: Failed to load plugins" >&2

# https://github.com/ajeetdsouza/zoxide
eval "$(zoxide init zsh --cmd cd)"

# 長時間実行コマンドの通知設定
source_and_zcompile_if_needed "${SET}shell/zsh/notification.zsh" || echo "Warning: Failed to load notification config" >&2

# NVM遅延ロード設定
export NVM_DIR="$HOME/.nvm"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  # 共通の初期化関数
  _lazy_load_nvm() {
    unset -f nvm node npm npx _lazy_load_nvm
    source "$NVM_DIR/nvm.sh"
    [[ -s "$NVM_DIR/bash_completion" ]] && source "$NVM_DIR/bash_completion"
  }

  # 遅延ロード用のラッパー関数
  nvm() { _lazy_load_nvm && nvm "$@" }
  node() { _lazy_load_nvm && node "$@" }
  npm() { _lazy_load_nvm && npm "$@" }
  npx() { _lazy_load_nvm && npx "$@" }

  # .nvmrc自動読み込み機能(遅延ロード対応版)
  load-nvmrc() {
    [[ ! -f .nvmrc ]] && return 0

    # nvmが遅延ロード状態なら初期化
    typeset -f _lazy_load_nvm >/dev/null 2>&1 && _lazy_load_nvm

    local required_version="$(cat .nvmrc)"
    local current_version="$(nvm version 2>/dev/null)"
    local installed_version="$(nvm version "$required_version" 2>/dev/null)"

    if [[ "$installed_version" == "N/A" ]]; then
      echo "Installing Node.js version from .nvmrc: $required_version"
      nvm install "$required_version"
    elif [[ "$installed_version" != "$current_version" ]]; then
      nvm use "$required_version" >/dev/null 2>&1
    fi
  }

  # chpwd_functionsに登録
  autoload -U add-zsh-hook
  add-zsh-hook chpwd load-nvmrc

  # 初回読み込み時にも実行
  load-nvmrc
fi

if $IS_VSCODE && command -v code >/dev/null 2>&1; then
  . "$(code --locate-shell-integration-path zsh)" 2>/dev/null || true
fi

# 自動コンパイル
# http://blog.n-z.jp/blog/2013-12-10-auto-zshrc-recompile.html
zcompile_if_needed ~/.zshrc

# ローカル設定（上書き用）
source_and_zcompile_if_needed ~/.zshrc_local
