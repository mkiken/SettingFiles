---
allowed-tools: Bash(gh:*)
description: "Generate comprehensive PR body content using gh command for specified PR number"
---

## Instructions

- Use the gh command to fetch and analyze PR #$ARGUMENTS
  - Generate content suitable for PR body
  - Exclude template sections
- Format in markdown with bullet points
- Include the following sections:
  - **Summary**: Comprehensive overview grouped by logical changes
  - **Files Changed Summary**: File-by-file breakdown of changes with brief descriptions
  - **Review Focus Points**: Areas requiring special attention during review
  - **Breaking Changes**: Any breaking changes or migration requirements
  - **Additional Notes**: Any other relevant information for reviewers
- **Output to file**: Save the generated PR body content to `/tmp/pr-body-$ARGUMENTS.md` for future reference and easy copying
