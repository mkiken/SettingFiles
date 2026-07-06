Provided: metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag, repo owner/name; do not refetch them. Local mode: `read_file`, `glob("**/*test*")`, `glob("**/*spec*")`, `grep_search`; otherwise read files/tree with `gh api` via `run_shell_command`.

Rules:
- Changed/new code is primary. Report missing tests for unchanged code only when the untested path creates critical outage or data-loss risk; prefix `[既存コード]` and name the category.
