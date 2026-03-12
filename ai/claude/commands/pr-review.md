---
allowed-tools: Bash(gh:*)
description: "Comprehensive PR review using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- Use the gh command to fetch and analyze PR #$ARGUMENTS for comprehensive code review
- Provide detailed review feedback in the following structured format:

### **Remote Review Workflow**

Fetch primary review materials:
- `gh pr view $ARGUMENTS --json title,body,files,commits,baseRefName,headRefName` — PR metadata
- `gh pr diff $ARGUMENTS` — Complete diff (**Note: file path arguments are not supported; always fetch the full diff and filter locally if needed**)
- `gh pr view $ARGUMENTS --comments` — Existing comments

For deeper investigation (referencing files outside diff, checking surrounding context):
- `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d` — Read any file
- `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` — Explore file structure

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

**Output must be grouped by priority level in descending order. Omit priority levels with no findings:**

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

