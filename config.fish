#environment variables
set REPO "$HOME/Desktop/repository";
set SET "$REPO/SettingFiles";
set SUBMODULE_DIR "$SET/submodules";
set MACVIM "/Applications/MacVim.app/Contents/MacOS/mvim"
set FISHCONFIG "$HOME/.config/fish/config.fish"
set PECO_CONFIG "$SET/peco.config"
set CD_HISTORY_FILE $HOME/.cd_history_file # cd 履歴の記録先ファイル
set LOCAL_FISH_CONFIG "$HOME/.fishrc"

#editor
alias vs='env LANG=ja_JP.UTF-8 $MACVIM'
alias vi='vs --remote-tab-silent'
# TODO これどうする？
alias vimdiff='env LANG=ja_JP.UTF-8 $MACVIM''diff'
alias vimrc='vi $HOME/.vimrc'
alias st='subl'
alias at='atom'

#open file
alias config='vi $FISHCONFIG'
alias tmuxconf='vi $HOME/.tmux.conf'
alias gitconfig='vi $HOME/.gitconfig'
alias macinit='vi $SET/mac/initialize'
alias macupdate='vi $SET/mac/update'
alias tigrc='vi ~/.tigrc'
alias pecoconfig='vi $PECO_CONFIG'
alias aliases='vi $HOME/.aliases'
alias fishrc='vi $LOCAL_FISH_CONFIG'

# common
alias reload='source $FISHCONFIG; and echo "config reloaded."'
alias t='tig'
alias ng='noglob'
alias pg='sudo purge'
alias cask='brew cask'
# http://tukaikta.blog135.fc2.com/blog-entry-214.html
alias rm='rmtrash'
# 事故死予防
alias cp='cp -i'
alias mv='mv -i'
alias pv='popd'

# ls
alias l='ls'
alias la='ls -a'
alias ll='ls -l'

# ag
alias ag='ag -S --stats -m 100000 --color'
alias agh='ag --hidden'
alias agl='ag -l'
alias agg='ag -g' # ファイル名で検索

# cd
alias cdd="cd $HOME/Desktop"
alias cdr="cd $REPO"
alias cds="cd $SET"
alias up='cd ..'

# tmux
alias tm='tmux'
alias tmks='tmux kill-server'

# git
alias g='git'
alias gs='git s'
alias gps='git push'
alias gmd='git modified'
alias gd='g diff'
alias gdc='gd --cached'
alias gst='g stash'
alias gstp='gst pop'
alias gdn='gd --name-status'
alias grm='g rm'
alias gco='g checkout'
alias gmg='g merge'
alias gft='g fetch'
alias gftp='gft --prune'

function gpl
  g pl (g remote) (g current-branch)
end

# https://github.com/fish-shell/fish-shell/issues/1640#issuecomment-53384451
function chpwd --on-variable PWD
  status --is-command-substitution; and return
  ls
  echo $PWD >> $CD_HISTORY_FILE # peco_cd_history 用
end

# for prompt
# http://mariuszs.github.io/informative_git_prompt/
# https://github.com/fish-shell/fish-shell/pull/880/files
set -g __fish_git_prompt_show_informative_status 1
set -g __fish_git_prompt_hide_untrackedfiles 1

set -g __fish_git_prompt_color_branch magenta
set -g __fish_git_prompt_showupstream "informative"
set -g __fish_git_prompt_char_upstream_ahead "↑"
set -g __fish_git_prompt_char_upstream_behind "↓"
set -g __fish_git_prompt_char_upstream_prefix ""

set -g __fish_git_prompt_char_stagedstate "●"
set -g __fish_git_prompt_char_dirtystate "✚"
set -g __fish_git_prompt_char_untrackedfiles "…"
set -g __fish_git_prompt_char_conflictedstate "✖"
set -g __fish_git_prompt_char_cleanstate "✔"

set -g __fish_git_prompt_color_dirtystate blue
set -g __fish_git_prompt_color_stagedstate yellow
set -g __fish_git_prompt_color_invalidstate red
set -g __fish_git_prompt_color_untrackedfiles $fish_color_normal
set -g __fish_git_prompt_color_cleanstate green

function fish_prompt -d "Write out the prompt"

    if [ $status -eq 0 ]
        set color green
    else
        set color red
    end

    printf "%s%s %s%s:%s \$" (set_color -o $color) (prompt_pwd) (set_color normal) (__fish_git_prompt)
end

# function fish_prompt
  # echo (pwd)" ><(((o> "
# end

if test -e $PECO_CONFIG
  source $PECO_CONFIG
end

# load local setting.
# TODO あれば
if test -e $LOCAL_FISH_CONFIG
  source $LOCAL_FISH_CONFIG
end
