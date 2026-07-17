---
name: pr-review-subagents
description: >
  Comprehensive PR review using seven Codex custom subagents, parallelized up to the
  runtime limit, for bugs, security, architecture, error handling, git history, tests, and performance. Use when the
  user wants PR review with subagents, review-subagents, or parallel specialist
  reviewers. Accepts an optional PR number plus extra review instructions; if omitted,
  detect the current branch PR.
---

## Instructions

Review a PR with seven read-only specialist Codex subagents.

Inputs: parse the user's message as `[prNumber] [additionalInstructions...]`. If the first PR-like token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat any remaining request text as `<ADDITIONAL_INSTRUCTIONS>`:

```bash
gh pr view --json number --jq .number
```

Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, pass it to every subagent and apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Gather Once

Fetch context in the parent session:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,headRefName,headRefOid,url,files,commits
gh pr diff <PR_NUMBER>
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
git rev-parse HEAD
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>
```

Local mode = current branch matches `headRefName` **and** `git rev-parse HEAD` matches `headRefOid`. If either check fails, use remote mode: subagents must inspect the PR head with `gh api`, not local files. This prevents unpushed or unrelated local commits from being reviewed as part of the PR.

Capture the full and line-numbered diffs through the configured large-output path, using source labels unique to the PR and `headRefOid`. Count the line-numbered diff before expanding it in the parent context.

Before spawning, derive a compact existing-comment manifest from the NDJSON. Include one record for every top-level inline thread (`kind=inline` and `in_reply_to_id=null`) with `id`, `path`, `line`, `start_line`, `is_resolved`, `is_outdated`, `thread_id`, `ai_origin`, and a concise body excerpt that preserves the root cause and requested fix. Keep the full NDJSON in the parent for final aggregation.

Pass every subagent directly: PR number, metadata, repo owner/name, the compact comment manifest, local mode, base/head names, `headRefOid`, and `<ADDITIONAL_INSTRUCTIONS>`. For a line-numbered diff of at most 100 lines, also pass both diffs directly. For a larger diff, do not paste either full payload; pass the changed-file list and captured source labels instead. Every subagent must inspect every changed file and its relevant diff at the exact head revision (local mode: local head file plus `git diff <base>...<headRefOid>`; remote mode: `gh api` contents at `headRefOid` plus the PR-files patch). Indexed snippets alone are insufficient. Do not refetch the whole PR diff or make duplicate detection depend only on an indexed source. Each subagent's focus and review rules are in its definition.

### Spawn

Run all seven exactly once, parallelized up to the child-agent slots available at runtime:

- `pr_reviewer_bugs`
- `pr_reviewer_security`
- `pr_reviewer_architecture`
- `pr_reviewer_errors`
- `pr_reviewer_history`
- `pr_reviewer_tests`
- `pr_reviewer_performance`

If fewer than seven child-agent slots are available, use waves. Launch the maximum safe number, start the next specialist whenever a slot becomes free, and continue until all seven have completed. Never combine review dimensions merely to fit the slot limit.

Each subagent stays read-only and returns Japanese findings in its configured format.
Read-only includes not creating scratch files: never redirect diffs, comments, or command output to files in the repository or elsewhere.
Inspect the passed context or indexed sources, or run read-only commands directly.
