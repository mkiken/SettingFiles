---
name: pr-review
description: >
  Comprehensive PR review using gh command. Use this skill when the user wants to
  review a pull request, analyze a PR for bugs/security/architecture/readability,
  or says things like "PRレビューして", "review PR", "このPRをレビュー", "review pull request".
  Accepts an optional PR number; if not provided, detects from the current branch automatically.
---

## Instructions

Perform a comprehensive code review for the specified PR (or the PR associated with the current branch if no number is given), then report findings in the structured format defined in the core rules below.

PR number: extract from the user's message if provided. If not provided, run:
```bash
gh pr view --json number --jq .number
```

### Local vs Remote File Access

Determine the file access mode before starting:

1. `git branch --show-current` — current local branch
2. `gh pr view <PR_NUMBER> --json title,body,files,commits,baseRefName,headRefName` — PR metadata
3. Compare the current branch with `headRefName`.

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

### Review Scope: Changed Code vs Pre-existing Code

**Primary focus**: findings MUST target lines added or modified in this PR's diff. Do not surface issues whose root cause lives entirely in unchanged code this PR did not touch.

**Pre-existing-code exception (critical only)**: report an issue that exists entirely in unchanged code only when it falls into one of these critical impact categories:

- **Security breach**: concrete exploitable attack vector (auth bypass, RCE, injection, secret exposure)
- **Data corruption/loss**: silent overwrite, missing transaction, irreversible mutation
- **Service outage**: crash, infinite loop, deadlock, resource exhaustion under realistic load
- **Compliance violation**: PII handling, license breach, audit trail loss

Route such findings to `## 既存コードに関する指摘` (see routing below) and state the applicable category. All other pre-existing issues MUST be omitted.

### Priorities and Routing

Assign a priority to every finding:

- 🔴 **High (Action Required)**: bug risk, security vulnerabilities, data loss
- 🟡 **Medium (Recommended)**: architecture issues, performance, critical readability
- 🟢 **Low (Optional)**: maintainability, minor refactoring, style

Route each finding, deciding in this order:

1. `## 既存コードに関する指摘` — pre-existing-code findings per the critical-only exception above. Decided first: a pre-existing finding about tests still goes here, not in the test section. Each detail line must state the critical impact category (Security breach / Data corruption-loss / Service outage / Compliance violation).
2. `## テストに関する指摘` — missing tests, weak assertions, brittle tests, incorrect mocks/fixtures, boundary-value tests, negative/error-path tests, integration coverage. If a runtime bug and a missing test share the same root cause, keep the bug in the regular section and mention the missing test in its detail line; create a separate test finding only when a distinct test change is required.
3. Regular priority sections — everything else.

Within every section, group findings by priority in descending order and omit empty priority levels. Number all findings sequentially across regular, test, and pre-existing sections — never restart numbering per section. Omit `## テストに関する指摘` and `## 既存コードに関する指摘` entirely when they have no actionable findings.

### Code Quality Perspectives

Review thoroughly from all of these perspectives: **Bug Risk** (potential bugs, error handling), **Coding Standards** (general rules, best practices), **Architecture** (separation of concerns, class/function design), **Readability** (intent clarity, naming, comments), **Performance** (issues, optimization opportunities), **Security** (vulnerabilities, sensitive data handling), **Maintainability** (change flexibility, technical debt).

### Actionable Findings Only

Output only findings that require a concrete response: code changes, test additions, design changes, documentation updates, or explicit reviewer decisions. Do not output praise, compliance confirmations, or non-actionable observations ("looks good", "no issue here"). Omit the `Review Focus Points` and `Recommendations` sections unless they contain concrete unresolved actions not already covered by numbered findings.

If no actionable findings remain after deduplication, output only:

```markdown
対応が必要な指摘はありません。
```

### Existing Comment Deduplication

Before finalizing each finding, check whether it is already covered by an existing PR comment (fetched as NDJSON per the workflow above; fields: `id`, `kind`, `path`, `line`, `body`, `author`, `is_self`, `ai_origin`, `is_resolved`, `is_outdated`):

1. `is_resolved == true` or `is_outdated == true` → treat as non-existing. Re-reporting is allowed; append `(参考: 過去にresolved済みの既存コメント #<id> と同様の指摘)` to the detail line.
2. **Mark as duplicate** when: same `path` + line within ±5 AND same root cause, OR same target symbol/concept addressable by the same fix.
3. **Do NOT skip**: same problem type at a different file, or a more specific finding requiring a different fix.
4. Skip only when duplicate confidence is ≥ 70. Below 70, output both.
5. `ai_origin` (author being human/bot/AI) does not affect the duplicate decision — judge on content only.

When findings are skipped, add `## [既コメント済] スキップした指摘` immediately before the Post-Review block (omit entirely when nothing is skipped):

```
- **[path:line]** Category / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>
```

### Line Number Source

Use the `format_pr_diff_with_line_numbers.sh` output (fetched per the workflow above) as the authoritative source for final `[path:line]` references:

- `FILE <path>` — identifies the current file
- `NEW <line>` — added or changed line in the PR head; the preferred review target
- `CTX <line>` — unchanged context in the PR head; use only when a finding cannot be anchored to a `NEW` line
- `OLD <line>` — removed base-side code; never use in final review comments

Never calculate final review line numbers from `@@` hunk headers by memory. If a candidate finding is not present in the line-numbered diff, verify the exact current-side line (e.g. `grep -n`) or omit the finding.

### Finding Format

Each finding MUST use this exact three-part structure:

- **Header line**: `N. **[file:line]** Category: Short one-line summary` — path relative to repository root, `[path:line]` for single line or `[path:startLine-endLine]` for a range. Inside `## 既存コードに関する指摘`, append the critical impact category in parentheses.
- **Detail line**: `   - Full explanation and recommendation (indented sub-bullet)`. Do not cram the explanation into the header line.
- **Separator line**: `---` after every finding, including the last one — a hard structural requirement that must never be omitted.

Output skeleton (numbering continues across all sections):

#### 🔴 High Priority
1. **[src/services/auth.ts:42]** Security: Auth token may be exposed in logs
   - Token is logged in plaintext. Apply a masking utility before passing to logger.

---

#### 🟡 Medium Priority
2. **[src/components/Button.tsx:15-20]** Architecture: Consider separating logic
   - Click handler mixes UI event handling with business logic. Extract to a custom hook.

---

#### 🟢 Low Priority
3. **[src/utils/format.ts:8]** Readability: Use more descriptive variable names
   - `d` and `v` obscure intent; rename to `date` and `value` for clarity.

---

## テストに関する指摘

#### 🟡 Medium Priority
4. **[src/services/auth.test.ts:1]** Test Coverage: Missing negative-path test for session expiry
   - Add a test asserting `getUser()` behavior when the session has expired.

---

## 既存コードに関する指摘

#### 🔴 High Priority
5. **[src/db/query.ts:120]** Security: SQL injection in pre-existing helper (Security breach category)
   - Unchanged code called by this PR's new feature concatenates raw user input into a query string. Concrete attack vector: any string input allows arbitrary SQL execution.

---

### Post-Review: Clean Up & Post to GitHub

After completing the review, delete any temporary files you created during the process (e.g., `diff.txt`, `pr_diff.txt`).

If at least one actionable finding remains, display the following message after outputting the review results:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
