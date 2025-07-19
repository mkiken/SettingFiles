#!/bin/zsh
# Other aliases

EDIT_COMMAND='code'
export VISUAL='nvim'

# General aliases
alias l='ls'
alias -g L='| less'
alias vi='nv'
alias -g nvim-orig='nvim -u NONE --noplugin'
alias -g nv='nvim'

# 事故死予防
alias cp='cp -i'
alias mv='mv -i'

alias pv='popd'
alias ng='noglob'

# Commitizen
alias czc='cz commit'

# difit
alias di='npx difit'

# ripgrep
alias -g rg='RIPGREP_CONFIG_PATH=${SET}/configs/.ripgreprc rg'

# Vim runtime
VIMRUNTIME=$(nvim --clean --headless --cmd 'echo $VIMRUNTIME|q' 2>&1)
alias vless="${VIMRUNTIME}/scripts/less.sh"

# tail with color
function tailf(){
  tail -f "${@}" | gsed -f "${SET}sedfiles/colorize_log.sed"
}

# zmv
alias zmv='noglob zmv -W'
alias zcp='zmv -C'

# vimdiff
alias vimdiff='nvim-orig -d'
alias vd='vimdiff'

# util
alias sz='dust -d 1 -Dr'

# tig/gitui/lazygit
alias t='lazygit'

# up command
function up() {
	if test $# -lt 1; then
	    echo $#
	  cd ../
		return 0
  fi
  tmp=''
  repeat "$1" tmp+='../'
  cd "$tmp" || exit
}

# Path functions
function fullpath(){
  echo "${PWD}/${1}"
}

# gitのリポジトリルートからの相対パス
relpath() {
  file="${1}"
  if [[ -z "${file}" ]]; then
      echo "Usage: $0 <file>"
      return 1
  fi

  git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [[ $? -ne 0 ]]; then
      echo "Error: Not in a Git repository." >&2
      return 1
  fi

  file_abs=$(realpath "${file}" 2>/dev/null)
  if [[ -z "${file_abs}" ]]; then
      echo "Error: File '${file}' not found." >&2
      return 1
  fi

  git_root="${git_root%/}"
  if [[ "${file_abs}" != "${git_root}"/* ]]; then
      echo "Error: File is not inside the Git repository." >&2
      return 1
  fi

  rel_path="${file_abs#"${git_root}"/}"
  echo "${rel_path}"
}

alias fp='fullpath'
alias rp='relpath'

# make new alias
alias reload='zcompile ~/.zshrc;source ~/.zshrc;echo "zshrc reloaded.";zcompile ~/.zprofile;source ~/.zprofile;echo "zprofile reloaded."'
alias rm_zwc='rm ~/*.zwc;rm ${SET}/shell/zsh/*.zwc;echo "zwc removed."'

# cd shortcuts
alias cdd='cd ~/Desktop'
alias cdrepo='cd ${REPO}'
alias cds='cd ${SET}'

# shortcut for setting files
alias zshrc_local='${EDIT_COMMAND} ~/.zshrc_local'
alias zshenv='${EDIT_COMMAND} ~/.zshenv'
alias zprofile='${EDIT_COMMAND} ~/.zprofile'
alias setting='${EDIT_COMMAND} ${SET}'
alias s='setting'