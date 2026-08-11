## Rules

- Provided: PR metadata, full diff, line-numbered diff, local-mode flag, repo owner/name, existing comments NDJSON; do not re-fetch them.
- Enumerate the claims first — PR title/body, every commit message from the metadata, linked issue references (`gh issue view` / `gh api`, read-only) — then test each claim against the diff. In local mode, use `Read`; in remote mode, use `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d`.
- Anchor a mismatch to the diff line where reality diverges from the claim; for refutation by absence (e.g. "tested" but no test changed), anchor to the most relevant NEW line of the implementation change the claim covers.
- In local mode you may run existing tests read-only to check coverage claims; never modify files or state.
- Do not report a finding whose only substance is a code defect another dimension owns.
