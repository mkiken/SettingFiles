The parent provides metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag, and repo owner/name; do not refetch existing comments. In local mode use `read_file`/`glob`/`grep_search`; otherwise explore/read with `gh api` via `run_shell_command`.

Rules:
- Changed code is primary. Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
