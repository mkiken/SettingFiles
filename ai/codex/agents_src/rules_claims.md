Rules:
- Enumerate the claims first — PR title/body, every commit message from the metadata, linked issue references (`gh issue view` / `gh api`, read-only) — then test each claim against the diff.
- Anchor a mismatch to the diff line where reality diverges from the claim; for refutation by absence (e.g. "tested" but no test changed), anchor to the most relevant NEW line of the implementation change the claim covers.
- You may run existing tests read-only to check coverage claims; never modify files or state.
- Do not report a finding whose only substance is a code defect another dimension owns.
