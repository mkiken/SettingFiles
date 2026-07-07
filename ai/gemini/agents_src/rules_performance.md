Provided: metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag; do not refetch them. Local mode: `read_file`/`glob`/`grep_search`; otherwise `gh api` via `run_shell_command`.

Rules:
- Changed code is primary; read callers, loop bodies, and query call sites around changed code to prove a path is hot or repeated before reporting.
- Design-level scalability belongs to the architecture reviewer; report only concrete runtime cost introduced by this PR.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
