- please press ^T-I in tmux to install tmux plugins.

- You can write LOCAL settings for git to '~/.gitconfig.local'.

- Config overwrites you already reviewed once are auto-skipped on later runs.
  Pass '--reprompt-reviewed' to mac/initialize or mac/update to be asked again
  (equivalent to SETTINGFILES_DIFF_REVIEW_REPROMPT=1).
  Review records live in '${XDG_STATE_HOME:-$HOME/.local/state}/SettingFiles/diff-reviews';
  delete that directory to make every pending diff prompt again.
