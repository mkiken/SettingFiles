---
name: pr-review
description: >
  Comprehensive PR review using gh command. Use this skill when the user wants to
  review a pull request, analyze a PR for bugs/security/architecture/readability,
  or says things like "PRレビューして", "review PR", "このPRをレビュー", "review pull request".
  Accepts an optional PR number plus extra review instructions; if no PR is provided,
  detects from the current branch automatically.
---

## Instructions

Perform a comprehensive code review for the specified PR (or the PR associated with the current branch if no number is given), then report findings in the structured format defined in the core rules below.

Keep the review read-only and do not create scratch files: never redirect diffs, comments, or command output to files in the repository or elsewhere.
Inspect command output or indexed sources, or run read-only commands directly.

Inputs: parse the user's message as `[prNumber] [additionalInstructions...]`. If the first PR-like token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat any remaining request text as `<ADDITIONAL_INSTRUCTIONS>`:
```bash
gh pr view --json number --jq .number
```

Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Local vs Remote File Access

Determine the file access mode before starting:

1. `git branch --show-current` — current local branch
2. `gh pr view <PR_NUMBER> --json title,body,files,commits,baseRefName,headRefName --jq '{title,body,baseRefName,headRefName,files:[.files[]|{path,additions,deletions,changeType}],commits:[.commits[]|{oid,messageHeadline}]}'` — bounded PR metadata
3. Compare the current branch with `headRefName`.

Commit bodies, authors, and dates are intentionally omitted. If a headline needs investigation, fetch that commit on demand with `git show <oid> --no-patch` (local mode) or `gh api repos/{owner}/{repo}/commits/{oid}` (remote mode).

**If they match (local mode)** — investigate with the `Read` tool (faster, includes uncommitted local changes) and the `Glob` tool (e.g. `Glob("src/**/*.ts")`).

**If they don't match (remote mode)** — use gh api:
- `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d` — read any file
- `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` — explore file structure

### Review Workflow

Fetch primary review materials (PR metadata is already fetched above):

- `gh pr diff <PR_NUMBER>` — complete diff (file path arguments are not supported; always fetch the full diff and filter locally if needed)
- `bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>` — existing PR comments as NDJSON (inline, issue, and review-summary with resolved/outdated status)
- `bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>` — line-numbered diff; the authoritative source for review line numbers (see Line Number Source in the core rules)

For deeper investigation (files outside the diff, surrounding context), use the access mode determined above.

### Core Review Rules

### PR-Scoped Auxiliary Checks

Derive PR-scoped auxiliary checks from `gh pr diff <PR_NUMBER>` or exact PR base/head OIDs fetched from GitHub. Never infer PR scope from a local `<baseRefName>...HEAD` range; local branch refs may be stale or contain unrelated history. Local-mode reads may still inspect uncommitted working-tree context, but findings and PR-scoped checks must remain limited to the PR diff.

### Review Scope: Changed Code vs Pre-existing Code

**Primary focus**: findings MUST target lines added or modified in this PR's diff. Do not surface issues whose root cause lives entirely in unchanged code this PR did not touch.

**Pre-existing-code exception (critical only)**: report an issue that exists entirely in unchanged code only when it falls into one of these critical impact categories:

- **Security breach**: concrete exploitable attack vector (auth bypass, RCE, injection, secret exposure)
- **Data corruption/loss**: silent overwrite, missing transaction, irreversible mutation
- **Service outage**: crash, infinite loop, deadlock, resource exhaustion under realistic load
- **Compliance violation**: PII handling, license breach, audit trail loss

Route such findings to `## 既存コードに関する指摘` (see routing below) and state the applicable category. All other pre-existing issues MUST be omitted.

### Additional Review Instructions

If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, use it to prioritize investigation and reporting. It must not override mandatory duplicate detection, line-number, safety, or output-format rules.

### Priorities and Routing

Self-assess 影響度 and 信頼度 (0–100) for every finding and assign priority per the Output Format section below. Low 信頼度 never suppresses a finding — it only lowers priority.

Route each finding, deciding in this order:

1. `## 既存コードに関する指摘` — pre-existing-code findings per the critical-only exception above. Decided first: a pre-existing finding about tests still goes here, not in the test section. Each detail line must state the critical impact category (Security breach / Data corruption-loss / Service outage / Compliance violation).
2. `## テストに関する指摘` — missing tests, weak assertions, brittle tests, incorrect mocks/fixtures, boundary-value tests, negative/error-path tests, integration coverage. If a runtime bug and a missing test share the same root cause, keep the bug in the regular section and mention the missing test in its detail line; create a separate test finding only when a distinct test change is required.
3. Regular priority sections — everything else.

Within every section, group findings by priority in descending order. Omit `## テストに関する指摘` and `## 既存コードに関する指摘` entirely when they have no actionable findings.

### Code Quality Perspectives

Review thoroughly from all of these perspectives, using the Japanese label as the finding header's 領域: **バグリスク** (potential bugs, error handling), **コーディング規約** (general rules, best practices), **アーキテクチャ** (separation of concerns, class/function design), **可読性** (intent clarity, naming, comments), **パフォーマンス** (issues, optimization opportunities), **セキュリティ** (vulnerabilities, sensitive data handling), **保守性** (change flexibility, technical debt). Findings in `## テストに関する指摘` use 領域 **テスト品質**.

### Actionable Findings Only

Output only findings that require a concrete response: code changes, test additions, design changes, documentation updates, or explicit reviewer decisions. Do not output praise, compliance confirmations, or non-actionable observations ("looks good", "no issue here").

### Existing Comment Deduplication

Before finalizing each finding, check whether it is already covered by an existing PR comment (fetched as NDJSON per the workflow above; fields: `id`, `kind`, `path`, `line`, `body`, `author`, `is_self`, `ai_origin`, `is_resolved`, `is_outdated`):

1. Apply the same duplicate criteria below to every existing comment regardless of `is_resolved` / `is_outdated` — a resolved or outdated duplicate suppresses re-reporting exactly like an unresolved one.
2. **Mark as duplicate** when: same `path` + line within ±5 AND same root cause, OR same target symbol/concept addressable by the same fix.
3. **Do NOT skip**: same problem type at a different file, or a more specific finding requiring a different fix.
4. Skip only when duplicate confidence is ≥ 70. Below 70, output both.
5. `ai_origin` and `is_resolved`/`is_outdated` (author or thread state) do not affect the duplicate decision — judge on content only.

Record each skipped finding in the `[既コメント済]` section defined in the Output Format section below. When the matched comment is resolved or outdated, say so in the reason (e.g. `resolved済みの既存コメント #<id> と同一根本原因`).

### Line Number Source

Use the `format_pr_diff_with_line_numbers.sh` output (fetched per the workflow above) as the authoritative source for final `[path:line]` references:

- `FILE <path>` — identifies the current file
- `NEW <line>` — added or changed line in the PR head; the preferred review target
- `CTX <line>` — unchanged context in the PR head; use only when a finding cannot be anchored to a `NEW` line
- `OLD <line>` — removed base-side code; never use in final review comments

Never calculate final review line numbers from `@@` hunk headers by memory. If a candidate finding is not present in the line-numbered diff, verify the exact current-side line (e.g. `grep -n`) or omit the finding.

### Output Format

Respond entirely in Japanese.

**Priority mapping (影響度 × 信頼度)** — self-assessed per finding. 影響度: High = data loss/outage/vulnerability/broad breakage, Medium = limited malfunction or degradation, Low = minor. 信頼度 = 0–100 certainty that the issue is real. Priority: High = 影響度High & 信頼度>=75; Medium = 影響度Medium & 信頼度>=75, or 影響度High & 信頼度<75 (append 「要検証」 to the detail); Low = 影響度Low & notable, or 影響度Medium & 信頼度<75 (append 「要検証」). The mapping decides priority only, never whether a finding is reported — the calling skill's actionability rules decide that.

Each finding MUST use this exact three-part structure:

- **Header line**: `N. **[file:line]** 領域 (影響度: XX / 信頼度: XX): 短い一行の要約` — path relative to repository root, `[path:line]` for a single line or `[path:startLine-endLine]` for a range; 領域 is a Japanese area label from the calling skill's dimension list. Inside `## 既存コードに関する指摘`, append `（重大カテゴリ）` to the summary.
- **Detail line**: `   - Full explanation and recommendation (indented sub-bullet)`. Do not cram the explanation into the header line.
- **Separator line**: `---` after every finding, including the last one — a hard structural requirement that must never be omitted.

Number findings sequentially across all sections — never restart numbering per section.

Use this skeleton, omitting empty sections and empty priority levels. The calling skill may prepend extra leading sections (e.g. a summary table) before the first priority section:

```markdown
## 🔴 High Priority（影響度High・信頼度75+）

1. **[path/to/file.ext:line]** 領域 (影響度: XX / 信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority

2. （同形式）

## 🟢 Low Priority

3. （同形式）

## テストに関する指摘

### 🟡 Medium Priority

4. （同形式、領域はテスト品質）

## 既存コードに関する指摘

### 🔴 High Priority（影響度High・信頼度75+）

5. （同形式、要約末尾に重大カテゴリ）

## [既コメント済] スキップした指摘

- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```

Place `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line per skipped finding as shown; omit the section when nothing was skipped. `## 総合評価` states the merge verdict line plus a short overall comment.

If no actionable findings remain after deduplication, output only (no skeleton, no 総合評価):

```markdown
対応が必要な指摘はありません。
```

### Post-Review: Clean Up & Post to GitHub

After completing the review, delete any temporary files created during the process.

If at least one actionable finding remains, display the following message after outputting the review results:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
