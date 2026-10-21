---
name: branch-pr-task
description: Implement a request on a new branch cut from a proposed parent branch, then open a PR to that parent. Use for `$branch-pr-task` or an explicit branch-to-PR workflow.
---

# Branch PR Task

Invoke as `$branch-pr-task <implementation request>`. Treat the text after the invocation as the implementation request. If it is empty, ask for it through the platform's user-confirmation mechanism before changing anything.

Work in the current worktree. Defer the ambient post-implementation commit/push confirmation until this workflow finishes; the single confirmation below replaces it.

## Preconditions

Stop and report instead of working around the problem:

- `git symbolic-ref --short HEAD` fails (detached `HEAD`).
- `git status --porcelain` is non-empty: list the dirty paths. Never stash, clean, reset, or commit them to proceed.

## Choose the parent branch and branch name

1. `git fetch origin`.
2. Collect candidates: the current branch, the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`), and the most recently committed remote branches (`git branch -r --sort=-committerdate`, top few).
3. Pick one recommendation from the request: a branch or feature the request names, else the current branch when it is not the default branch, else the default branch.
4. Derive `<type>/<kebab-slug>` (`feat`, `fix`, `refactor`, `docs`, `chore`) from the request. If the local or `origin` branch exists, append `-2`, `-3`, and so on.
5. Ask once through the platform's user-confirmation mechanism: show the recommended parent first, then the other candidates, plus the branch name. The user corrects either through free-form input.

Create the branch from the confirmed parent, not from the current `HEAD`:

```bash
git switch -c <branch> origin/<parent>
```

On failure, stop and report; do not retry with a different base.

## Implement

Apply the request, obeying the repository's instructions (`CLAUDE.md` / `AGENTS.md`). Verify with the repository's documented test command scoped to the changed paths; if none exists, run the narrowest command that exercises the change and say so when nothing is executable. Remove only temporary artifacts created during this run. Do not commit during implementation.

If the work leaves nothing changed, report that and switch back to the original branch, then delete the new branch with `git branch -d`; skip every step below.

## Confirm once

Show the changed paths, verification results, the commit message (following the repository's convention), the PR title, and the PR body, fenced with a backtick fence longer than any fence inside the body. Ask exactly these options through the platform's user-confirmation mechanism:

1. `はい、作成する`
2. `titleを修正したい`
3. `bodyを修正したい`
4. `キャンセル`

On a modification choice, collect the correction, re-display, and ask again. On `キャンセル`, leave all changes uncommitted on the new branch, report its name, and stop. Commit, push, and PR creation happen only after `はい、作成する`.

### PR body

Describe the final state at HEAD only; never trial and error. Keep it brief and lead with the conclusion. If `.github/PULL_REQUEST_TEMPLATE.md` exists, use its structure instead.

````markdown
## Summary

- What this PR does and why, in 3 lines or fewer.

## 背景・目的

- Why this work was started, only when the request or conversation states a motive or history. Omit the whole section otherwise.

## 実装内容

- One bullet per logical change, by intent and effect. No per-file listing, no line counts.

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->
````

PR title: within 70 characters, conventional prefix when it fits, describing what changed and why.

## Commit, push, and create the PR

1. Stage only the paths changed for this task with explicit `git add <paths>`; never `git add -A` or `git add .`.
2. Verify the staged diff holds only intended hunks, then commit in the repository's message convention. On failure, preserve the state, report, and stop.
3. Push the new branch without force: `git push -u origin <branch>`. On failure, report and stop.
4. Create the PR with the body on stdin:

```bash
/bin/cat <<'PREOF' | gh pr create --base <parent> --title "<title>" --body-file -
<PR body>
PREOF
```

Verify independently: `git log -1`, `git ls-remote origin <branch>` equals the local `HEAD`, and `gh pr view --json url,baseRefName` reports base `<parent>`. Report an unmet check instead of claiming success.

## Report

Display the PR URL, then always display 「リマインド: PRのレビュワー設定を忘れないでください。」 Do not check whether reviewers are already assigned and do not offer to set them.
