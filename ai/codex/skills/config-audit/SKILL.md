---
name: config-audit
description: >
  Audit all Codex configuration files (AGENTS.md, config.toml, skills, agents,
  hooks, rules) for redundancy, conflicts, ambiguity, and unnecessary rules.
  Trigger keywords: "設定を監査", "コンフィグ監査", "設定の整理", "AGENTS.md最適化",
  "audit config", "clean up config", "check for conflicts", "optimize prompts".
---

## Instructions

- `PLATFORM_NAME` = `Codex`.
- `SCOPE` = the scope keyword in the user's message (empty → `all`).
- `ENTRY_SCOPE` = `agents-md`.
- `GENERATED_ENTRY_FILE` = `~/.codex/AGENTS.md`.
- `CONFIG_PATHS`:
  - Global: `~/.codex/AGENTS.md`, `~/.codex/config.toml`, `~/.codex/skills/*/SKILL.md`, `~/.codex/agents/*.toml`, `~/.codex/hooks.json`, `~/.codex/hooks/*`, `~/.codex/rules/*`
  - Project: `./AGENTS.md`, `./ai/codex/config.toml`, `./ai/codex/codex_base.md`, `./ai/codex/skills/*/skill_head.md`, `./ai/codex/agents/*.toml`, `./ai/codex/hooks.json`, `./ai/codex/rules/*`
  - Never audit runtime/state files under `~/.codex` (auth.json, history.jsonl, sessions/, cache, sqlite, logs).
- `SOURCE_FILES`: `ai/common/prompt_base.md`, `ai/common/characters/nyaruko.md`, `ai/codex/codex_base.md` (concatenated into the generated `_AGENTS.md`; audit the sources, not the generated file)
- For every user confirmation, ask a plain question and wait for the reply.

## Core Workflow

## Goal

Read all `PLATFORM_NAME` configuration files, evaluate every rule against five criteria, and report deletion candidates, conflicts, and an optimized configuration proposal.

## Scope

`SCOPE` narrows the audit target. Empty → `all`. Skip values with no corresponding files on this platform.

- `all` (default): every configuration file
- `ENTRY_SCOPE`: entry prompt files only
- `skills` / `commands` / `agents` / `hooks` / `settings`: that file type only
- `global`: global config only (project-level excluded)
- `project`: project-level only (global excluded)

## Workflow

### Phase 1: Discovery

Explore `CONFIG_PATHS` (in parallel where possible) and build a file manifest narrowed by `SCOPE`.

**Source-file mode:** if `GENERATED_ENTRY_FILE` is a symlink, resolve it with `readlink`; when the resolved file's ancestor repository contains `ai/common/prompt_base.md` and an `ai/common/characters/` directory, audit `SOURCE_FILES` individually instead of the generated entry file. Source-to-generated expansion is normal build behavior, not duplication.

Before proceeding, print the manifest as a `## 監査対象ファイル一覧` table with columns ファイル / 種別 / 備考.

### Phase 2: Extraction

Read every manifest file (in parallel where possible). Identify rules as semantic units — headings, bullets, prose instructions, frontmatter metadata, permission and hook settings — not mechanical line splits.

Attach to each rule: `source file` (path), `section` (enclosing heading, if any), `rule text`, and `category` — one of `behavior` (general behavioral guidance), `formatting` (output format), `workflow` (task procedures), `tool-usage`, `character` (persona settings from the adopted character file), `code-style`, `commit-convention`, `response-language`, `permission`.

**Exclusions:** files installed by third-party plugins or tools (e.g. Tsumiki) stay in the manifest but are excluded from analysis. Identify them by directory or filename prefix, or by symlinks resolving outside the dotfiles repository.

### Phase 3: Analysis

Evaluate each extracted rule against the five criteria below. `character` rules are intentional customization: apply only criterion 2 (conflict) to them.

**Criterion 1: Default behavior** — would the assistant do this without being told? (generic coding best practices, obvious safety instructions). Judge conservatively — do not flag rules that reinforce important behavior.

**Criterion 2: Conflict** — does it contradict another file or rule? (global vs project entry prompt, settings permissions vs skill tool allowlists, character settings vs behavior rules, skills/commands with overlapping purposes)

**Criterion 3: Duplication** — does it overlap another rule or file, as exact repeated text or semantic duplication (different wording, same instruction)?

**Criterion 4: One-off patch** — does it look added to fix one specific bad output rather than improve general quality? (very specific file paths or function names, wording implying a past incident 「〜しないように」「前回のように〜」, overly narrow rules for a single situation)

**Criterion 5: Ambiguity** — could each interpretation yield a different result? (subjective qualifiers 「より自然に」「適切に」, no clear pass/fail criterion, vague conditions 「場合による」「適宜」)

### Phase 4: Reporting

Output the structured report below in Japanese, in the conversation only — do not write any file.

**Item numbers are continuous across all report sections; never reset per section.**

In section 3, propose diffs for each file in `SOURCE_FILES` (or the audited files when source-file mode is off), only where changes are recommended.

````markdown
# {PLATFORM_NAME} 設定監査レポート

## 監査対象ファイル一覧
| ファイル | 種別 | ルール数 |
|---------|------|---------|
| ... | ... | N |

---

## 1. 削除・修正推奨項目

### 🔵 デフォルト動作と重複（指示なしでも実行される）
N. **[ファイル名 > セクション]** ルール要約
   - 理由: ...

### 🟡 ルール間の重複
N. **[ファイルA > セクション]** ← **[ファイルB > セクション]**
   - 重複内容: ...
   - 推奨: どちらを残すか

### 🟠 一時的な修正（汎用的でない）
N. **[ファイル名 > セクション]** ルール要約
   - 理由: ...

### ⚪ 曖昧・解釈が不安定
N. **[ファイル名 > セクション]** ルール要約
   - 問題点: ...
   - 改善案: より具体的な表現の提案

---

## 2. コンフリクト一覧
N. **[ファイルA > セクション]** ↔ **[ファイルB > セクション]**
   - 内容A: ...
   - 内容B: ...
   - 推奨: どちらを優先すべきか / どう統合するか

---

## 3. 最適化された設定ファイル案

### 変更サマリー
- 削除推奨: N件
- 修正推奨（曖昧 → 具体的）: N件
- 統合推奨（重複解消）: N件

### ファイル別の推奨変更

#### <ファイル名>
```diff
- 削除推奨の行
+ 修正推奨の行（該当する場合）
```
````

### Phase 5: Follow-up

After the report, confirm the next action with the user:

1. **推奨変更の全適用** — apply every proposed change
2. **番号指定で部分適用** — apply only the items named by their continuous serial numbers (e.g. 「1, 3, 5 を適用」)
3. **特定セクションの深掘り** — analyze one area in more depth
4. **レポートのファイル保存** — save the report to a file

Ending without action or any other request is expressed as a free-form reply (or the auto-provided "Other" choice), not a listed option.

Apply file changes only after explicit user approval.

## Notes

- Character files are intentional customization — report only, never propose optimization.
- Locally accumulated permission entries (e.g. `settings.local.json`) are mostly one-off approvals — flag as cleanup candidates, but be cautious about deletion.
- Exclude the currently running skill's own instructions — audit persistent configuration files only.
- If the report is long, print summary tables first and details in later sections.
