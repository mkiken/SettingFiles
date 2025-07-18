---
allowed-tools: Bash(gh:*)
description: "Generate comprehensive PR body content using gh command for specified PR number"
---
ultrathink

## Instructions
- Use the gh command to fetch and analyze PR #$ARGUMENTS
  - Generate content suitable for PR body
  - Exclude template sections
- Include the following sections:
  - **Summary**: Comprehensive overview grouped by logical changes
  - **Files Changed Summary**: File-by-file breakdown of changes with brief descriptions
  - **Review Focus Points**: Areas requiring special attention during review
  - **Breaking Changes**: Any breaking changes or migration requirements
  - **Additional Notes**: Any other relevant information for reviewers
- Output **raw markdown format** that can be directly copied to PR body
  - Wrap the PR body output with ``` code blocks
- **Output to file**: Ask the user if they want to save the generated PR body content to a file for future reference and easy copying. If yes, save to `/tmp/pr-body-$ARGUMENTS.md`
