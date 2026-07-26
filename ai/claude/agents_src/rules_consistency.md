## Rules

- Provided: PR metadata, full diff, line-numbered diff, local-mode flag, repo owner/name, existing comments NDJSON; do not re-fetch them.
- In local mode, use `Glob`/`Grep`/`Read`; in remote mode, use `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` and content API reads.
- Findings are anchored to changed code only, but the comparison target is the wider repo: search for existing code doing the same or a similar job and read it before reporting.
- No precedent, no finding: cite the existing counterpart path in 比較対象. A convention repeated across 2+ existing locations is evidence; a single divergent example or personal preference is not.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
