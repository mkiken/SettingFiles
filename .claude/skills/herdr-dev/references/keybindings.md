# Herdr keybindings

When adding or changing key bindings in `terminal/herdr/config.toml`, Herdr is an environment independent of tmux — ignore tmux (`.tmux.conf`) bindings even though both share the `ctrl+t` prefix. Do not judge conflicts from the committed `config.toml` alone: it lists only overrides, while Herdr ships ~146 default action bindings (e.g. `prefix+g`=goto, `prefix+shift+g`=new_worktree). Confirm the live default keymap with `herdr --default-config` before choosing a key. Specifically check whether the chosen key already carries a default action absent from `config.toml` (e.g. `prefix+shift+w`=rename_workspace) — binding over an unlisted default silently shadows it without showing up as a diff or conflict in the committed file.

Binding a key to a `[[keys.command]]` popup: see `popups.md`.
