Provided: metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag, repo owner/name; do not refetch them. Local mode: `read_file`/`glob`/`grep_search`; otherwise `gh api` via `run_shell_command`.

Rules:
- Findings are anchored to changed code only, but the comparison target is the wider repo: search for existing code doing the same or a similar job and read it before reporting.
- No precedent, no finding: cite the existing counterpart path in 比較対象. A convention repeated across 2+ existing locations is evidence; a single divergent example or personal preference is not.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
