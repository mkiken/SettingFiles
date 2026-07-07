---
name: config-audit
description: >
  Audit all Codex configuration files (AGENTS.md, config.toml, skills, agents,
  hooks, rules) for redundancy, conflicts, ambiguity, and unnecessary rules.
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

### Spawn

In Phase 2, spawn all six in parallel and wait for all, passing the payload defined there:

1. **config_auditor_default** — デフォルト動作との重複
2. **config_auditor_conflict** — コンフリクト
3. **config_auditor_overlap** — ルール間の重複
4. **config_auditor_patch** — 一時的な修正
5. **config_auditor_ambiguity** — 曖昧なルール
6. **config_auditor_concise** — 意味を変えないトークン削減

## Core Workflow

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

Before dispatching, print the manifest as a `## 監査対象ファイル一覧` table with columns ファイル / 種別 / 備考.

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
5. Build section 3's per-file diffs from the surviving deletions, ambiguity rewrites, and shortenings — targeting `SOURCE_FILES` when source-file mode is on, the audited files otherwise.

## Phase 4: Report

Output the structured report below in Japanese, in the conversation only — do not write any file.

````markdown
# {PLATFORM_NAME} 設定監査レポート

## 監査対象ファイル一覧
| ファイル | 種別 | 備考 |
|---------|------|------|
| ... | ... | ... |

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

### 🟢 冗長な表現（意味を変えない短縮）
N. **[ファイル名 > セクション]** 対象要約
   - 現状: ...
   - 短縮案: ...
   - 削減見込み: 約N語

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
- 短縮推奨: N件

### ファイル別の推奨変更

#### <ファイル名>
```diff
- 削除推奨の行
+ 修正推奨の行（該当する場合）
```
````

## Phase 5: Follow-up

After the report, confirm the next action with the user:

1. **推奨変更の全適用** — apply every proposed change
2. **番号指定で部分適用** — apply only the items named by their continuous serial numbers (e.g. 「1, 3, 5 を適用」)
3. **特定セクションの深掘り** — analyze one area in more depth
4. **レポートのファイル保存** — save the report to a file

Ending without action or any other request is expressed as a free-form reply (or the auto-provided "Other" choice), not a listed option.

Apply file changes only after explicit user approval.

## Notes

- Exclude the currently running skill's own instructions — audit persistent configuration files only.
- If the report is long, print summary tables first and details in later sections.
