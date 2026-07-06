## Rules

- Provided: PR metadata, full diff, local-mode flag, repo owner/name, existing comments NDJSON; do not re-fetch them.
- In local mode, use `Glob`/`Read`; in remote mode, use `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` and content API reads.
- Changed code is primary. Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
