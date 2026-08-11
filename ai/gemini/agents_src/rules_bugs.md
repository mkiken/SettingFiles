Provided: metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag, repo owner/name; do not refetch them. Local mode: `read_file`/`glob`/`grep_search`; otherwise `gh api` via `run_shell_command`.

Rules:
- Changed code is primary; read surrounding context only to prove behavior or trace an error path.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
