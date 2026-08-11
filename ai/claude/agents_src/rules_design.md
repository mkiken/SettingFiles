## Rules

- Provided: PR metadata, full diff, line-numbered diff, local-mode flag, repo owner/name, existing comments NDJSON; do not re-fetch them.
- In local mode, use `Glob`/`Grep`/`Read`; in remote mode, use `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` and content API reads.
- Findings are anchored to changed code only, but for consistency findings the comparison target is the wider repo: search for existing code doing the same or a similar job and read it before reporting. No precedent, no finding: cite the existing counterpart path in 比較対象/現状. A convention repeated across 2+ existing locations is evidence; a single divergent example or personal preference is not.
- Simplification findings are suggestions, not defects: propose only clear wins (obviously easier to read and maintain — skip marginal rewrites, clever one-liners, and line-count golf), at most the 5 most valuable, and never for unchanged pre-existing code; use 影響度 Low by default, Medium only when the complexity actively obscures the change's behavior, never High. 信頼度 is your certainty that the rewrite is behavior-preserving and clearly better.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
