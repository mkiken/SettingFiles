---
allowed-tools: Bash(gh:*)
description: "Generate comprehensive PR body content using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- Before generating the body, check if `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root
  - If it exists, use its structure as the base for the PR body. Fill in each section with the generated content.
  - If it does not exist, use the default section format defined below.
- First, fetch and review the existing PR body using `gh pr view $ARGUMENTS --json body`
  - If the existing body contains meaningful information (not just template text), preserve and incorporate it
  - Template-only content (placeholders, empty sections) can be discarded
- Use the gh command to fetch and analyze PR #$ARGUMENTS
  - Generate content suitable for PR body
  - Exclude template sections
- Analyze the full diff and describe the PR based on the **final state (HEAD)**, not intermediate steps
  - Do not mention reverted changes, overwritten intermediate states, or trial-and-error in the history
  - Background information useful to reviewers (why this approach was chosen, alternatives considered) is acceptable
- Include the following sections:
  - **Summary**: Comprehensive overview grouped by logical changes
  - **Files Changed Summary**: File-by-file breakdown with brief descriptions (DO NOT include line counts like +X/-Y)
  - **Review Focus Points**: Check the existing PR body for this section. If the existing body contains non-default content (anything other than "特になし" or empty), preserve the existing content exactly. Only write "特になし" when creating a new PR body or when the existing section is empty/default.
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
   - Apply the body using stdin pipe to avoid shell escaping issues:
     ```bash
     cat <<'EOF' | gh pr edit $ARGUMENTS --body-file -
     <generated PR body here>
     EOF
     ```
   - Show success message with PR URL
   - Display: "必要に応じて **Review Focus Points** を確認・編集してください"

5. If user declines:
   - End process (user can manually copy the displayed content)
