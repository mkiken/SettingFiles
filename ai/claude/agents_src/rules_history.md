## Rules

- You receive PR metadata, full diff, repo owner/name, and existing comments NDJSON; the comments are for deduplication only — do not re-fetch them or confuse them with past PR evidence.
- Use history commands such as `gh api repos/{owner}/{repo}/commits?path={file}&per_page=10`, `gh pr list --state merged --limit 20 --json number,title,files`, and `gh pr view {number} --comments`.
- Changed code is primary. Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
