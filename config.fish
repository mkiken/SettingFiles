#environment variables
set REPO "$HOME/Desktop/repository";
set SET "$REPO/SettingFiles";
set MACVIM "/Applications/MacVim.app/Contents/MacOS/mvim"
set FISHCONFIG "$HOME/.config/fish/config.fish"
set PECOCONFIG "$SET/peco.config"

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

# tmux
alias tm='tmux'
alias tmks='tmux kill-server'

# git
alias g='git'
alias gs='git s'
alias gps='git push'

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

source $PECOCONFIG
