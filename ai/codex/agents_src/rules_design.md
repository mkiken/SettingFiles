Rules:
- In local mode, use `rg`, `git`, `sed`, and `gh` for targeted inspection. In remote mode, use `gh api` against `headRefName`.
- Findings are anchored to changed code only, but for consistency findings the comparison target is the wider repo: search for existing code doing the same or a similar job and read it before reporting.
- No precedent, no finding: cite the existing counterpart path in 比較対象/現状. A convention repeated across 2+ existing locations is evidence; a single divergent example or personal preference is not.
- Simplification findings are suggestions, not defects: propose only clear wins, at most the 5 most valuable, and never for unchanged pre-existing code; use 影響度 Low by default, Medium only when the complexity actively obscures the change's behavior, never High.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.
