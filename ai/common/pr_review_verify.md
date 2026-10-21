### Verify Findings

Adversarially verify every finding in a fresh context before final output. Any finding that depends on a specific external CLI/API/parser/library behavior or output format additionally needs a minimal reproduction against the applicable version or an authoritative primary source; without one, report it only as `要検証` with confidence below 75, or drop it.

1. If there are zero findings, skip this stage entirely.
2. Launch the dedicated verifier subagent (name and launch primitive per the platform instructions above) once, batched over all findings. Pass exactly: each finding verbatim (header, 行番号根拠, detail), repo owner/name, PR number, local-mode flag, `baseRefOid`/`headRefOid`, cited file paths, and captured source labels. Do not pass your own reasoning or aggregation history — the verifier must judge from primary sources only.
3. The verifier attempts to REFUTE each finding and returns per-finding verdicts with evidence.
4. Merge verdicts — confirmed: keep as is; refuted: drop it and subtract it from the summary counts; unverifiable: append 「要検証: <理由>」 to its detail, and downgrade it to Medium if it was High (Medium/Low keep their priority). Treat a missing or garbled verdict as unverifiable, never as confirmed.
5. Only if the session cannot launch a subagent, run the same protocol inline as a skeptical batched pass: read each cited head-revision file at most once with enough context to test the claim (local mode: read the file; remote mode: `gh api` contents), and actively seek refuting evidence — existing guards or validation, unreachable paths, framework/library behavior, tests proving the claimed failure cannot occur, or a misread diff.
6. If any finding was refuted or downgraded, add one line before `## 総合評価`: `検証により指摘 N 件を棄却、High M 件を Medium に降格しました。`
