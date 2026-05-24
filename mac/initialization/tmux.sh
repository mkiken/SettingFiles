#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

function setup_tmux_symlinks() {
  local -a tmux_scripts=(
    new-window.py
    sort-windows.py
    rename-window-git.sh
    fzf-jump-window.sh
    open-nv.sh
    new-session.sh
    cycle-session.sh
    select-session.sh
    update-session-ai-status.sh
    resurrect-save-wrapper.sh
    resurrect-restore-wrapper.sh
    resurrect-setup.sh
    split-snapshot-pane.sh
    tmux-file-picker.sh
  )

  make_symlink "${Repo}.tmux.conf" ~/.tmux.conf

  local script
  for script in "${tmux_scripts[@]}"; do
    make_symlink "${Repo}shell/tmux/${script}" "${HOME}/.tmux/scripts/${script}"
  done
}

function setup_tmux_plugin_manager() {
  local tpm_dir="${HOME}/.tmux/plugins/tpm"

  if [[ ! -d "${tpm_dir}/.git" ]]; then
    git clone https://github.com/tmux-plugins/tpm "${tpm_dir}"
  fi

  if [[ -f "${tpm_dir}/bin/install_plugins" ]]; then
    "${tpm_dir}/bin/install_plugins"
  fi
}

setup_tmux_symlinks
setup_tmux_plugin_manager

echo 'Tmux configured.'
