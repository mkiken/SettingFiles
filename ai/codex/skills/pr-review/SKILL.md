---
name: pr-review
description: >
  Comprehensive PR review using gh command. Use this skill when the user wants to
  review a pull request, analyze a PR for bugs/security/architecture/readability,
  or says things like "PRレビューして", "review PR", "このPRをレビュー", "review pull request".
  Accepts an optional PR number; if not provided, detects from the current branch automatically.
---

## Instructions

Perform a comprehensive code review for the specified PR (or the PR associated with the current branch if no number is given).

PR number: extract from the user's message if provided. If not provided, run:
```bash
gh pr view --json number --jq .number
```

### Local vs Remote File Access

Before starting the review, determine the file access mode:

1. Run `git branch --show-current` to get the current local branch name
2. Fetch PR metadata: `gh pr view <PR_NUMBER> --json title,body,files,commits,baseRefName,headRefName`
3. Compare the current branch with `headRefName`

**If they match (local mode)** — use local tools for deeper investigation:
- Use the `Read` tool to read file contents directly (faster, includes uncommitted local changes)
- Use the `Glob` tool to explore file structure (e.g., `Glob("src/**/*.ts")`)

**If they don't match (remote mode)** — use gh api:
- `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d` — Read any file
- `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` — Explore file structure

### Review Workflow

Fetch primary review materials:
- PR metadata is already fetched in the step above
- `gh pr diff <PR_NUMBER>` — Complete diff (**Note: file path arguments are not supported; always fetch the full diff and filter locally if needed**)
- `bash "$(git rev-parse --show-toplevel)/shell/common/pr/fetch_existing_comments.sh" <PR_NUMBER>` — Existing PR comments as NDJSON (inline, issue, and review-summary with resolved/outdated status)

For deeper investigation (referencing files outside diff, checking surrounding context), use the method determined above.

### Existing Comment Deduplication

Before finalizing each finding, check whether it is already covered by an existing PR comment:

1. **Skip resolved/outdated from duplicate matching**: `is_resolved == true` or `is_outdated == true` → non-existing. Re-reporting is allowed; append `(参考: 過去にresolved済みの既存コメント #<id> と同様の指摘)` to the detail line.
2. **Mark as duplicate** when: same `path` + line within ±5 AND same root cause, OR same target symbol/concept addressable by the same fix.
3. **Do NOT skip**: same problem type at a different file, or a more specific finding requiring a different fix.
4. **Confidence threshold**: skip only when your duplicate confidence is ≥ 70. Below 70, output both.
5. `ai_origin` does not affect the duplicate decision — judge on content only.

When findings are skipped, add **`## [既コメント済] スキップした指摘`** immediately before the Post-Review block:
```
- **[path:line]** Category / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>
```
Omit this section entirely when nothing is skipped.

### Review Comment Priority

Assign priority to all review comments:

- 🔴 **High (Action Required)**: Bug risk, security vulnerabilities, data loss
- 🟡 **Medium (Recommended)**: Architecture issues, performance, critical readability
- 🟢 **Low (Optional)**: Maintainability, minor refactoring, style

**Group output by priority in descending order.**

### Code Quality Review

Review thoroughly from the following perspectives:

- **Bug Risk**: Potential bugs and error handling issues
- **Coding Standards**: Adherence to general rules and best practices
- **Architecture**: Separation of concerns, appropriate class/function design
- **Readability**: Code intent clarity, naming conventions, comments
- **Performance**: Performance issues and optimization opportunities
- **Security**: Security vulnerabilities and sensitive data handling
- **Maintainability**: Future change flexibility, avoiding technical debt

**IMPORTANT**: For each review comment, specify the full file path (relative to repository root) and line number(s) in the following format:

- `[path/to/file.ext:line]` for single line comments
- `[path/to/file.ext:startLine-endLine]` for multi-line comments

**Number all findings sequentially across all priority sections (continue numbering across sections — do not restart per section).**

**Output must be grouped by priority level in descending order. Omit priority levels with no findings.**

**Finding Format**: Each item MUST use this exact three-part structure — header, detail, then separator:
- **Header line**: `N. **[file:line]** Category: Short one-line summary`
- **Detail line**: `   - Full explanation and recommendation (indented sub-bullet)`
- **Separator line**: `---` (horizontal rule — MANDATORY after every finding, including the last one)

The `---` separator after each item is a hard structural requirement that must never be omitted.

✅ CORRECT:

1. **[src/auth.ts:42]** Security: Token may be exposed in logs
   - Auth token is passed directly to the logger. Add a masking step before logging to prevent credential leakage.

---

2. **[src/auth.ts:87]** Bug Risk: Null check missing before user lookup
   - `user` can be null when session expires mid-request, causing an unhandled TypeError.

---

❌ WRONG (missing `---` separator and/or single long line):

1. **[src/auth.ts:42]** Security: Auth token may be exposed in logs because it is passed directly to the logger without masking, which could lead to credential leakage in log aggregation systems.
2. **[src/auth.ts:87]** Bug Risk: Null check missing before user lookup which can cause unhandled TypeError.

#### 🔴 High Priority
1. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

#### 🟡 Medium Priority
2. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

#### 🟢 Low Priority
3. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

### Review Focus Points

- Areas requiring special attention
- Regions needing additional testing
- Documentation update requirements

### Recommendations

- Specific improvement suggestions
- Alternative implementation approaches (if needed)

---

### Post-Review: Clean Up & Post to GitHub

After completing the review, delete any temporary files you created during the process (e.g., `diff.txt`, `pr_diff.txt`).

After outputting the review results, display the following message to the user:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
