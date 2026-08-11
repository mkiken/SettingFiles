Provided: metadata, full diff, line-numbered diff, existing comments NDJSON, local-mode flag, repo owner/name; do not refetch them. Local mode: `read_file`/`glob`/`grep_search`; otherwise `gh api` via `run_shell_command`.

Rules:
- Enumerate the claims first — PR title/body, every commit message from the metadata, linked issue references (`gh issue view` / `gh api` via `run_shell_command`, read-only) — then test each claim against the diff.
- Anchor a mismatch to the diff line where reality diverges from the claim; for refutation by absence (e.g. "tested" but no test changed), anchor to the most relevant NEW line of the implementation change the claim covers.
- In local mode you may run existing tests read-only to check coverage claims; never modify files or state.
- Do not report a finding whose only substance is a code defect another dimension owns.
