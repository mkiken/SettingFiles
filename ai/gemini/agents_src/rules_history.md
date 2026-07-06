Provided: metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag, repo owner/name. For history, use `run_shell_command`, e.g. `gh api repos/{owner}/{repo}/commits?path={file}&per_page=10`, `gh pr list --state merged --limit 20 --json number,title,files`, and `gh pr view {number} --comments`.

Rules:
- Changed code is primary. Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
