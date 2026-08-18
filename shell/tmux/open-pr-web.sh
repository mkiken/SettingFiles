#!/bin/zsh
# Open the current branch's GitHub pull request and keep the popup visible on failure.

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

function _current_branch_name() {
  local branch
  branch=$(git branch --show-current 2>/dev/null)
  if [[ -n "$branch" ]]; then
    print -r -- "$branch"
    return
  fi

  local commit
  commit=$(git rev-parse --short HEAD 2>/dev/null)
  if [[ -n "$commit" ]]; then
    print -r -- "detached HEAD ($commit)"
    return
  fi

  print -r -- "取得できませんでした"
}

gh pr view --web
exit_status=$?

if (( exit_status == 0 )); then
  exit 0
fi

print -u2 -- ""
print -u2 -- "PRを開けませんでした。"
print -u2 -- "現在のディレクトリ: $PWD"
print -u2 -- "現在のブランチ: $(_current_branch_name)"
print -u2 -- "終了コード: $exit_status"
print -u2 -- ""
print -u2 -- "Enterで閉じます。"
# 共通ラッパー(herdr-popup-run.sh)へpause済みを通知し二重待ちを防ぐ
[[ -n "${HERDR_POPUP_PAUSE_MARK:-}" ]] && print -r -- "open-pr-web" >> "${HERDR_POPUP_PAUSE_MARK}" 2>/dev/null
read -r _

exit "$exit_status"
