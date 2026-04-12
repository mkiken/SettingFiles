---
description: >
  Audit all Claude Code configuration files for redundancy, conflicts, ambiguity,
  and unnecessary rules. Analyzes CLAUDE.md, skills, commands, agents, hooks, and
  settings across global (~/.claude/) and project-level configs. Use when the user
  wants to clean up config, check for conflicts, optimize prompts, or reduce token
  consumption. Trigger keywords: "設定を監査", "コンフィグ監査", "設定の整理",
  "ルールの重複チェック", "CLAUDE.md最適化", "audit config", "clean up config",
  "check for conflicts", "optimize prompts", "config redundancy", "設定ファイルを整理",
  "CLAUDE.mdを最適化".
model: opus
argument-hint: "[scope: all|claude-md|skills|commands|agents|hooks|settings]"
---

## Overview

Claude Codeの全設定ファイルを読み込み、各ルール・指示を5つの基準で評価して、削除推奨項目・コンフリクト一覧・精簡版CLAUDE.mdを出力する。

## Arguments

- `$ARGUMENTS` format: `<scope>`
  - **scope** (optional): 監査対象の絞り込み
    - `all` (default): 全設定ファイルを監査
    - `claude-md`: CLAUDE.mdファイルのみ
    - `skills`: スキルファイルのみ
    - `commands`: コマンドファイルのみ
    - `agents`: エージェントファイルのみ
    - `hooks`: フックファイルのみ
    - `settings`: settings.jsonのみ
    - `global`: `~/.claude/` 配下のみ（プロジェクトレベル除外）
    - `project`: プロジェクトレベルのみ（グローバル除外）

`$ARGUMENTS` が空の場合は `all` として処理する。

---

## Workflow

### Phase 1: Discovery（設定ファイルの探索）

スコープに応じて以下を Glob で探索し、ファイルマニフェストを構築する。

**グローバル設定（`~/.claude/`）:**
- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`
- `~/.claude/settings.local.json`
- `~/.claude/skills/*/SKILL.md`
- `~/.claude/commands/**/*.md`
- `~/.claude/agents/*.md`
- `~/.claude/hooks/*`

**プロジェクトレベル設定（カレントディレクトリ）:**
- `./CLAUDE.md`
- `./.claude/CLAUDE.md`
- `./.claude/settings.local.json`

**シンボリックリンクの解決:**
`~/.claude/CLAUDE.md` がシンボリックリンクの場合、`readlink` で実体パスを確認する。実体パスが `_CLAUDE.md` であり、同じディレクトリ配下に以下のソースファイルが存在する場合は**ソースファイルモード**で動作する:

```bash
readlink ~/.claude/CLAUDE.md
```

ソースファイルモードの判定条件（実体ファイルの親ディレクトリを起点として探索）:
- `ai/common/prompt_base.md` が存在する
- `ai/common/characters/` ディレクトリが存在する
- `ai/claude/claude_prompt.md` が存在する

ソースファイルモードが有効な場合、`~/.claude/CLAUDE.md`（生成ファイル）ではなく以下を個別に分析する:
- `ai/common/prompt_base.md`
- `ai/common/characters/reimu.md`（または存在するキャラクターファイル）
- `ai/claude/claude_prompt.md`

探索完了後、マニフェストをテーブル形式で表示してから次のフェーズに進む:

```
## 監査対象ファイル一覧

| ファイル | 種別 | 備考 |
|---------|------|------|
| ~/.claude/CLAUDE.md | global-claude-md | → ai/claude/_CLAUDE.md (生成ファイル) |
| ai/common/prompt_base.md | source-claude-md | _CLAUDE.md のソース |
| ...
```

---

### Phase 2: Extraction（ルールの抽出）

マニフェスト内の全ファイルを Read で読み込む。各ファイルから以下を意味的に識別する（機械的な箇条書き分割ではなく、意味単位で抽出）:

- マークダウンの見出し・箇条書き・散文中の指示
- YAMLフロントマター（スキル・コマンド）のメタデータ設定
- settings.json の権限ルール・フック設定

各ルールに属性を付与:
- `ソースファイル`: 実際に記述されているファイルパス
- `セクション`: 属する見出し（あれば）
- `ルール内容`: ルールのテキスト
- `カテゴリ`: 以下のいずれか
  - `behavior` — Claudeの一般的な行動指針
  - `formatting` — 出力形式・フォーマット
  - `workflow` — タスク実行手順
  - `tool-usage` — ツール使用に関するルール
  - `character` — キャラクター設定（霊夢等）
  - `code-style` — コーディングスタイル
  - `commit-convention` — コミットメッセージ規約
  - `response-language` — 返答言語設定
  - `permission` — ツール権限設定

**除外対象:**
サードパーティプラグインのファイル（SuperClaude `sc:*`、Kiro、Tsumiki等）は一覧表示するが、監査対象外とする。ファイル名のプレフィックス・ディレクトリ名から判別する。

---

### Phase 3: Analysis（5基準での評価）

抽出した各ルールを以下5つの基準で評価する。`character` カテゴリのルールは基準2（コンフリクト）のみ評価し、それ以外の基準は適用しない（意図的な設定であるため）。

**基準1: デフォルト動作**
「指示しなくてもClaudeが通常行う行動か？」
- 例: 一般的なコーディングベストプラクティス、明らかな安全性指示
- 保守的に判定すること — 重要な動作を強化するルールは誤検知しないよう注意

**基準2: コンフリクト**
「他のファイル・ルールと矛盾または相反するか？」
- グローバルCLAUDE.md vs プロジェクトCLAUDE.md
- settings.jsonの権限 vs スキルの`allowed-tools`
- キャラクター設定 vs 行動ルール（例: Radical Honesty vs キャラクター性格）
- 類似目的のスキル同士（例: `pr-review` コマンド vs `pr-review-subagents` スキル）

**基準3: 重複**
「別のルールまたはファイルと内容が被っているか？」
- 完全一致（別ファイルに同じテキスト）
- 意味的重複（表現は違うが同じ指示）
- ソースファイル → `_CLAUDE.md` への展開は重複として扱わない（ビルドシステムの正常動作）

**基準4: 一時修正**
「全体的な品質改善ではなく、特定の悪い出力を修正するために追加されたように見えるか？」
- 非常に具体的なファイルパス・関数名が含まれる
- 「〇〇しないように」「前回のように〇〇すること」等の過去事例を示唆する表現
- 一つの特定状況にしか適用されない過度に細かいルール

**基準5: 曖昧さ**
「解釈するたびに異なる結果になりうるか？」
- 主観的な修飾語（「より自然に」「良いトーンで」「適切に」）
- 明確な合否基準がない
- 「場合による」「適宜」等の曖昧な条件

---

### Phase 4: Reporting（レポート出力）

日本語で以下の構造化レポートを出力する。**ファイルへの書き込みは行わず、会話内出力のみ。**

---

```markdown
# 設定監査レポート

## 監査対象ファイル一覧
| ファイル | 種別 | ルール数 |
|---------|------|---------|
| ... | ... | N |

---

## 1. 削除推奨項目

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

## 3. 最適化されたCLAUDE.md案

### 変更サマリー
- 削除推奨: N件
- 修正推奨（曖昧 → 具体的）: N件
- 統合推奨（重複解消）: N件

### ソースファイル別の推奨変更

#### prompt_base.md
```diff
- 削除推奨の行
+ 修正推奨の行（該当する場合）
```

#### characters/reimu.md
（変更なし / 変更あり）

#### claude_prompt.md
```diff
- 削除推奨の行
+ 修正推奨の行（該当する場合）
```
```

---

### Phase 5: Follow-up（フォローアップ）

レポート出力後、AskUserQuestion で次のアクションを確認する:

- 推奨変更の適用（特定項目の変更を実行するか）
- 特定セクションの深掘り（「スキルだけもっと詳しく」等）
- レポートのファイル保存

ファイルへの実際の変更は、ユーザーが確認・承認した場合のみ行う。

---

## Notes

- キャラクター設定（霊夢等）は最適化の対象外 — 意図的なカスタマイズとして報告のみ
- settings.local.json の権限設定は蓄積された一回限りの承認が多い — クリーンアップ候補として別途フラグを立てるが、削除は慎重に
- 現在実行中のスキル自身の指示はキャッシュから除外 — 永続的な設定ファイルのみ監査対象
- レポートが長くなる場合はサマリーテーブルを先に出力し、詳細は後続セクションに分ける
