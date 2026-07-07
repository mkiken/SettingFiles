### Review Scope: Changed Code vs Pre-existing Code

**Primary focus**: findings MUST target lines added or modified in this PR's diff. Do not surface issues whose root cause lives entirely in unchanged code this PR did not touch.

**Pre-existing-code exception (critical only)**: report an issue that exists entirely in unchanged code only when it falls into one of these critical impact categories:

- **Security breach**: concrete exploitable attack vector (auth bypass, RCE, injection, secret exposure)
- **Data corruption/loss**: silent overwrite, missing transaction, irreversible mutation
- **Service outage**: crash, infinite loop, deadlock, resource exhaustion under realistic load
- **Compliance violation**: PII handling, license breach, audit trail loss

Route such findings to `## 既存コードに関する指摘` (see routing below) and state the applicable category. All other pre-existing issues MUST be omitted.

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

Output only findings that require a concrete response: code changes, test additions, design changes, documentation updates, or explicit reviewer decisions. Do not output praise, compliance confirmations, or non-actionable observations ("looks good", "no issue here"). Omit the `Review Focus Points` and `Recommendations` sections unless they contain concrete unresolved actions not already covered by numbered findings.

### Existing Comment Deduplication

Before finalizing each finding, check whether it is already covered by an existing PR comment (fetched as NDJSON per the workflow above; fields: `id`, `kind`, `path`, `line`, `body`, `author`, `is_self`, `ai_origin`, `is_resolved`, `is_outdated`):

1. `is_resolved == true` or `is_outdated == true` → treat as non-existing. Re-reporting is allowed; append `(参考: 過去にresolved済みの既存コメント #<id> と同様の指摘)` to the detail line.
2. **Mark as duplicate** when: same `path` + line within ±5 AND same root cause, OR same target symbol/concept addressable by the same fix.
3. **Do NOT skip**: same problem type at a different file, or a more specific finding requiring a different fix.
4. Skip only when duplicate confidence is ≥ 70. Below 70, output both.
5. `ai_origin` (author being human/bot/AI) does not affect the duplicate decision — judge on content only.

Record each skipped finding in the `[既コメント済]` section defined in the Output Format section below.

### Line Number Source

Use the `format_pr_diff_with_line_numbers.sh` output (fetched per the workflow above) as the authoritative source for final `[path:line]` references:

- `FILE <path>` — identifies the current file
- `NEW <line>` — added or changed line in the PR head; the preferred review target
- `CTX <line>` — unchanged context in the PR head; use only when a finding cannot be anchored to a `NEW` line
- `OLD <line>` — removed base-side code; never use in final review comments

Never calculate final review line numbers from `@@` hunk headers by memory. If a candidate finding is not present in the line-numbered diff, verify the exact current-side line (e.g. `grep -n`) or omit the finding.
