---
allowed-tools: Bash(gh pr view *), Bash(gh pr checkout *), Bash(git status *), Bash(git stash *)
description: "Comprehensive PR review using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- Use the gh command to fetch and analyze PR #$ARGUMENTS for comprehensive code review
- Provide detailed review feedback in the following structured format:

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

**Output must be grouped by priority level in descending order:**

#### 🔴 High Priority
- **[path/to/file.ext:line]** Category: Issue description

#### 🟡 Medium Priority
- **[path/to/file.ext:line]** Category: Issue description

#### 🟢 Low Priority
- **[path/to/file.ext:line]** Category: Issue description

Example:

#### 🔴 High Priority
- **[src/services/auth.ts:42]** Security: Auth token may be exposed in logs

#### 🟡 Medium Priority
- **[src/components/Button.tsx:15-20]** Architecture: Consider separating logic

#### 🟢 Low Priority
- **[src/utils/format.ts:8]** Readability: Use more descriptive variable names

### **Review Focus Points**

- Areas requiring special attention
- Regions needing additional testing
- Documentation update requirements

### **Recommendations**

- Specific improvement suggestions
- Alternative implementation approaches (if needed)

### **Local Checkout for Detailed Review**

When PR diff is insufficient for judgment, checkout locally:

1. Check working files with `git status --porcelain`
2. If working files exist, ask user to choose:
   - Stash then checkout
   - Checkout anyway (may lose changes)
   - Cancel checkout
3. After approval, run `gh pr checkout <PR#>` (run `git stash` first if stash chosen)
4. Read local code for detailed review
