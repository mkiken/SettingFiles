---
allowed-tools: Bash(gh:*)
description: "Generate comprehensive PR body content using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- First, fetch and review the existing PR body using `gh pr view $ARGUMENTS --json body`
  - If the existing body contains meaningful information (not just template text), preserve and incorporate it
  - Template-only content (placeholders, empty sections) can be discarded
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

## Confirmation Flow

After generating the PR body content:

1. Display the generated body in a code block

2. **Display visual diff** between existing body and new body:
   - Show section header: "### 既存body → 新bodyの変更差分"
   - Use `diff` code block format for color-highlighted diff:
     ```diff
     - removed line (shown in red)
     + added line (shown in green)
       unchanged line
     ```
   - If existing body is empty/template-only: display "(既存bodyは空またはテンプレートのみのため、全て新規追加)"
   - Keep diff concise: for very large changes, summarize with key sections

3. Use AskUserQuestion to confirm: "このPR bodyをPR #$ARGUMENTS に反映しますか？"
   - Options: "はい、反映する" / "いいえ、表示のみ"

4. If user confirms:
   - Execute `gh pr edit $ARGUMENTS --body-file <temp-file>` to apply the body
   - Show success message with PR URL

5. If user declines:
   - End process (user can manually copy the displayed content)

## Implementation Notes

- Create temporary file for body content to avoid shell escaping issues
- Clean up temporary file after use
- Verify gh pr edit command success and show appropriate feedback
