## Rules

- Provided: PR metadata, full diff, line-numbered diff, local-mode flag, repo owner/name, existing comments NDJSON; do not re-fetch them.
- In local mode, use `Read` plus `Glob("**/*test*")` and `Glob("**/*spec*")`; in remote mode, use content API reads and `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1`.
- Read both implementation and tests when judging coverage.
- Changed/new code is primary. Report missing tests for unchanged code only when the untested path creates critical outage or data-loss risk; prefix `[既存コード]` and name the category.
