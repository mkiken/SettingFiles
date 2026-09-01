## Goal

Audit every `PLATFORM_NAME` configuration file with six parallel specialist agents, then report deletion candidates, conflicts, ambiguities, meaning-preserving shortenings, and an optimized configuration proposal.

## Scope

`SCOPE` narrows the audit target. Empty → `all`. Skip values with no corresponding files on this platform.

- `all` (default): every configuration file
- `ENTRY_SCOPE`: entry prompt files only
- `skills` / `commands` / `agents` / `hooks` / `settings`: that file type only
- `global`: global config only (project-level excluded)
- `project`: project-level only (global excluded)

## Phase 1: Discovery

Explore `CONFIG_PATHS` (in parallel where possible) and build a file manifest narrowed by `SCOPE`.

**Source-file mode:** if `GENERATED_ENTRY_FILE` is a symlink, resolve it with `readlink`; when the resolved file's ancestor repository contains `ai/common/prompt_base.md` and an `ai/common/characters/` directory, audit `SOURCE_FILES` individually instead of the generated entry file.

Files installed by third-party plugins or tools (e.g. Tsumiki) stay in the manifest marked 対象外 and are excluded from analysis. Identify them by directory or filename prefix, or by symlinks resolving outside the dotfiles repository.

Record the manifest for `audit.json`'s `manifest[]` (fields `file` / `type` / `note`; 対象外 goes in `note`). Do not print it — the report shows it.

## Phase 2: Dispatch

Launch all six auditor agents (named in the platform instructions above) in parallel, passing each the same payload:

1. `PLATFORM_NAME` and the resolved `SCOPE`
2. The manifest including 対象外 marks; in source-file mode, the `SOURCE_FILES` list to audit
3. The instruction: read the listed files yourself, evaluate only your own dimension, respond in Japanese in your configured format

Each agent's criterion and output format live in its definition — do not restate them. Do not pass `CONFIG_PATHS`.

## Phase 3: Aggregate

1. Drop 該当なし responses; count that dimension as zero findings.
2. Spot-check that each finding's quoted rule text exists in the cited file; drop mismatches.
3. Deduplicate findings on the same rule across dimensions, keeping the highest-precedence one: `conflict > patch > default > overlap > ambiguity > concise`. A surviving deletion proposal (patch/default/overlap) absorbs concise and ambiguity findings on the same rule — fold them into its detail.
4. Number items continuously across all report sections; never reset per section.
5. Detect same-location collisions: when two items target the same file and section and one item's edit would remove text the other depends on (e.g. a deletion candidate that also serves as a conflict's resolution, or two conflicting edits to the same rule), record each item's id in the other's `depends_on`. The report blocks applying one without the other, so an unrecorded dependency lets a single-item apply silently reintroduce or worsen the other item's problem.
6. Build each item's own `diff` from the surviving deletions, ambiguity rewrites, and shortenings — targeting `SOURCE_FILES` when source-file mode is on, the audited files otherwise. Per item, not per file: the user applies items selectively, and a per-file diff cannot be split.

## Phase 4: Report

Resolve `RUN_DIR` (see adapter) and write `<RUN_DIR>/audit.json`. Then render and serve the report.
Start the server **without** `--open` through a mechanism that survives the current command environment.
Obtain its URL and independently confirm that `<URL>/report.html` responds successfully before opening
that URL in a browser exactly once. If the server start fails, retry only the server start and
verification; never open a browser before verification or repeat the browser-open step. A supported
fallback is:

```bash
python3 ~/.config/ai-pr/bin/generate_audit_report.py <RUN_DIR>/audit.json <RUN_DIR>/report.html
nohup python3 ~/.config/ai-pr/bin/serve_review_report.py <RUN_DIR> >/dev/null 2>&1 &
```

Do not print the report body, the manifest table, the item list, or the diffs — they are all in the
report. Print only a Japanese summary: per-category counts, total items, dependency pair count, and
the follow-up usage — each item is decided as ✅ 適用する / 🚫 対応しない, and the decisions save
directly to `state.json` in <RUN_DIR>; use the save button or accept the confirmation after all items
are decided, then run the `audit-fix` skill to apply them. To reopen the report later (the report
server stops after being idle), the user runs the
**zsh shell function** `audit-report` (or `audit-report <platform>`) instead of opening `report.html`
directly — not a skill, so it is absent from the skill list; verify with `type audit-report`. It
reuses a live server for this run or starts a new one, so state saves stay server-backed instead of
falling back to a file-save dialog. Present it as a shell command, never as a skill.

### audit.json schema

```json
{
  "schema_version": 1,
  "platform": "{PLATFORM_NAME}",
  "platform_key": "claude",
  "scope": "all",
  "source_file_mode": true,
  "run_dir": "/abs/path/to/run",
  "generated_at": "2026-09-01T11:30:00+09:00",
  "manifest": [
    {"file": "~/.claude/CLAUDE.md", "type": "entry", "note": ""},
    {"file": "~/.claude/skills/foo/SKILL.md", "type": "skill", "note": "対象外（Tsumikiプラグイン）"}
  ],
  "summary": {"default": 3, "overlap": 2, "patch": 1, "ambiguity": 4, "concise": 6, "conflict": 2},
  "items": [
    {
      "id": 1,
      "category": "default",
      "file": "ai/common/prompt_base.md",
      "section": "## Output Rules",
      "targets": [{"file": "ai/common/prompt_base.md", "section": "## Output Rules"}],
      "summary": "one-line Japanese summary",
      "quote": "the rule text verbatim as it appears in the file",
      "details": [{"label": "理由", "text": "..."}],
      "depends_on": [4],
      "diff": "--- a/ai/common/prompt_base.md\n+++ b/ai/common/prompt_base.md\n-removed line\n",
      "estimated_reduction": null
    }
  ]
}
```

`category` is one of `default` / `overlap` / `patch` / `ambiguity` / `concise` / `conflict` — the five
deletion/fix groups plus conflicts, flattened into one key. `targets` holds every cited location: 2
entries for `overlap` (残す ← 重複) and `conflict` (A ↔ B), 1 otherwise; `file` and `section` mirror
`targets[0]`. `quote` is load-bearing twice — the report locates the surrounding context by searching
for it, and audit-fix re-checks it before editing — so it must match the file byte for byte. `details`
carries the same labelled bullets as before, in order (理由 / 重複内容 / 推奨 / 問題点 / 改善案 /
現状 / 短縮案 / 内容A / 内容B). `depends_on` lists item ids that must be applied together and must be
symmetric. `diff` is that item's own unified diff, or `null` when it has no mechanical edit.
`estimated_reduction` is the word count saved, `concise` only, `null` otherwise. `platform_key` is the
`audit-report` argument (`claude` / `codex` / `gemini`).

## Next: 適用

This skill ends at the report — it never edits a configuration file. Once every item is decided in the
browser and `state.json` is saved, the user runs the **`audit-fix`** skill (optionally with the run
directory) to apply the decisions. `audit-fix` selects ids whose `decision` is `"apply"` (✅ 適用する)
and leaves `"dismiss"` (🚫 対応しない) and `null` (未判断) alone.
Never fall back to asking for item numbers in the conversation, never read or write
`<RUN_DIR>/state.json` here — the browser owns it — and never apply an edit from this skill.

Name this follow-up in the Phase 4 summary.

## Notes

- Exclude the currently running skill's own instructions — audit persistent configuration files only.
