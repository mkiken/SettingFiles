---
allowed-tools: Bash(gh:*), Bash(git:*), Read, Glob
description: "Comprehensive PR review using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- Use the gh command to fetch and analyze PR #$ARGUMENTS for comprehensive code review
- Provide detailed review feedback in the following structured format:

### **Local vs Remote File Access**

Before starting the review, determine the file access mode:

1. Run `git branch --show-current` to get the current local branch name
2. Fetch PR metadata: `gh pr view $ARGUMENTS --json title,body,files,commits,baseRefName,headRefName`
3. Compare the current branch with `headRefName`

**If they match (local mode)** — use local tools for deeper investigation:
- Use the `Read` tool to read file contents directly (faster, includes uncommitted local changes)
- Use the `Glob` tool to explore file structure (e.g., `Glob("src/**/*.ts")`)

**If they don't match (remote mode)** — use gh api:
- `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d` — Read any file
- `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` — Explore file structure

### **Review Workflow**

Fetch primary review materials:
- PR metadata is already fetched in the step above
- `gh pr diff $ARGUMENTS` — Complete diff (**Note: file path arguments are not supported; always fetch the full diff and filter locally if needed**)
- `gh pr view $ARGUMENTS --comments` — Existing comments

For deeper investigation (referencing files outside diff, checking surrounding context), use the method determined above.

### **Review Comment Priority**

Assign priority to all review comments:

- 🔴 **High (Action Required)**: Bug risk, security vulnerabilities, data loss
- 🟡 **Medium (Recommended)**: Architecture issues, performance, critical readability
- 🟢 **Low (Optional)**: Maintainability, minor refactoring, style

**Group output by priority in descending order.**

### **Code Quality Review**

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

2. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

#### 🟡 Medium Priority
3. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

4. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

#### 🟢 Low Priority
5. **[path/to/file.ext:line]** Category: Short summary
   - Detailed explanation and recommendation.

---

Example:

#### 🔴 High Priority
1. **[src/services/auth.ts:42]** Security: Auth token may be exposed in logs
   - Token is logged in plaintext. Apply a masking utility before passing to logger.

---

2. **[src/services/auth.ts:87]** Bug Risk: Null check missing before user lookup
   - `getUser()` returns null on session expiry; add a null guard to prevent TypeError.

---

#### 🟡 Medium Priority
3. **[src/components/Button.tsx:15-20]** Architecture: Consider separating logic
   - Click handler mixes UI event handling with business logic. Extract to a custom hook.

---

#### 🟢 Low Priority
4. **[src/utils/format.ts:8]** Readability: Use more descriptive variable names
   - `d` and `v` obscure intent; rename to `date` and `value` for clarity.

---

### **Review Focus Points**

- Areas requiring special attention
- Regions needing additional testing
- Documentation update requirements

### **Recommendations**

- Specific improvement suggestions
- Alternative implementation approaches (if needed)

---

### **Post-Review: Post to GitHub**

After outputting the review results, display the following message to the user:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)

