Rules:

- Read the files listed in the dispatch payload yourself; skip entries marked 対象外. Read-only — never modify any file.
- Treat rules as semantic units — headings, bullets, prose instructions, frontmatter metadata, permission and hook settings — not mechanical line splits.
- Cite every finding as ファイル > セクション plus the exact quoted rule text; the orchestrator verifies quotes and builds diffs from them.
- Before finalizing a finding's quoted text, grep the whole repository for the same or a near-identical phrase and list every other file it appears in — shared cores (`ai/common/*_core.md`) commonly duplicate one rule across files, so a single-file finding often misses its propagation targets.
- `character` rules (persona settings from the adopted character file) are intentional customization: only the conflict dimension evaluates them; every other dimension skips them.
- Locally accumulated permission entries (e.g. `settings.local.json`) are mostly one-off approvals — cleanup candidates, but be cautious about deletion.
- Source-to-generated expansion is normal build behavior, never a finding.
- Report only findings needing concrete action; when unsure, do not flag.
