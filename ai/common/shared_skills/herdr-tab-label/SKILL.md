---
name: herdr-tab-label
description: Set the active Herdr tab's initial task label without overwriting a manual name. Use for the first substantive Codex task in a conversation, or when worktree-task needs one shared slug for its branch and Herdr tab.
---

# Herdr Tab Label

Derive one task slug, then make a single fail-safe attempt to use it as the active Herdr tab label. Reuse an existing caller-provided slug instead of deriving a second one.

## Derive the slug

Derive a short English slug from the task prompt:

- Use lowercase ASCII letters, digits, and hyphens only.
- Collapse separators and trim leading or trailing hyphens.
- Identify the affected target and intended change, with distinguishing terms first.
- Do not use a generic name made only of words such as `task`, `change`, `update`, or `fix` when the prompt provides specific terms.
- Use `task` only if no meaningful slug remains.

## Apply the label

If the active collaboration mode forbids side effects, do not rename the tab. Derive the slug again and apply it at the first implementation turn.

Record the task's absolute invoking working directory as `task_path`; callers such as `worktree-task` reuse their already-recorded invoking path. Then run:

```bash
herdr_label_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/herdr_status_icon.sh"
zsh -ic 'builtin cd -q -- "$1" && source "$2" && set_herdr_task_tab_label "$3"' zsh "$task_path" "$herdr_label_helper" "$slug"
```

Keep the `-c` script literal and pass the path, helper, and slug only as positional arguments. The helper is a no-op outside Herdr and preserves any non-default label. It keeps the jump-key number, AI identifier, status glyph, and context badge, and truncates a long slug to 19 characters plus `…`.

Treat exit zero as success, including intentional preservation of a manual label. If the helper is missing or the rename fails, report a tab-label warning and continue the main task. Do not retry during later ordinary tasks in the same Codex conversation; another workflow may explicitly reuse this procedure with its existing slug.
