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

### **Review Focus Points**
- Areas requiring special attention
- Regions needing additional testing
- Documentation update requirements

### **Recommendations**
- Specific improvement suggestions
- Alternative implementation approaches (if needed)

- **Output to file**: Ask the user if they want to save the generated review content to a file for future reference and easy copying. If yes, save to `/tmp/pr-review-$ARGUMENTS.md`