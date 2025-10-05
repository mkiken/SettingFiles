---
allowed-tools: Bash(gh:*)
description: "Comprehensive PR review using gh command for specified PR number"
model: claude-opus-4-1
argument-hint: [prNumber]
---
ultrathink

## Instructions

- Use the gh command to fetch and analyze PR #$ARGUMENTS for comprehensive code review
- Provide detailed review feedback in the following structured format:

### **Code Quality Review**
Review thoroughly from the following perspectives:
- **Bug Risk**: Potential bugs and error handling issues
- **Coding Standards**: Adherence to general rules and best practices
- **Architecture**: Separation of concerns, appropriate class/function design
- **Readability**: Code intent clarity, naming conventions, comments
- **Performance**: Performance issues and optimization opportunities
- **Security**: Security vulnerabilities and sensitive data handling
- **Maintainability**: Future change flexibility, avoiding technical debt

**IMPORTANT**: For each review comment, specify the file path and line number(s) in the following format:
- `[filename.ext:line]` for single line comments
- `[filename.ext:startLine-endLine]` for multi-line comments

Example format:
- **[src/auth.ts:42]** Bug Risk: Potential null pointer exception when user.email is undefined
- **[components/Button.tsx:15-20]** Readability: Consider extracting this logic into a separate function

### **Review Focus Points**
- Areas requiring special attention
- Regions needing additional testing
- Documentation update requirements

### **Recommendations**
- Specific improvement suggestions
- Alternative implementation approaches (if needed)

- **Output to file**: Ask the user if they want to save the generated review content to a file for future reference and easy copying. If yes, save to `/tmp/pr-review-$ARGUMENTS.md`