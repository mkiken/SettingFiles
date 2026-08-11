## Rules

- Provided: PR metadata, full diff, line-numbered diff, local-mode flag, repo owner/name, existing comments NDJSON; do not re-fetch them.
- Changed code is primary; read surrounding context only to prove behavior or trace an error path. In local mode, use `Read`; in remote mode, use `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d`.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
