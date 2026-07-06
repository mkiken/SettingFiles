## Rules

- You receive PR metadata, full diff, local-mode flag, repo owner/name, and existing comments NDJSON; do not re-fetch existing comments.
- In local mode, use `Read`/`Glob`; in remote mode, use `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d`.
- Changed code is primary. Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
