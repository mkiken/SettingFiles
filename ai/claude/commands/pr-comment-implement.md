---
allowed-tools: Bash(gh:*), Read, Edit, Write, Bash(git:*)
description: "Implement code changes based on PR review comments, with design review phase before implementation."
model: claude-opus-4-1
argument-hint: [prCommentUrl] [instructions...]
---
ultrathink

## Instructions
- Interpret the first argument from `$ARGUMENTS` as the PR comment URL (`$PR_URL`) and the rest as implementation instructions (`$PROMPT`).
- Use `gh pr view $PR_URL --comments` to fetch the review comments. The `gh` command automatically resolves the PR from the comment URL.
- Follow the structured workflow below to implement the requested changes.

## Workflow

### Phase 1: Analysis
1. Fetch and analyze the PR comments related to `$PR_URL`
2. Understand the issue or improvement request based on `$PROMPT`
3. Identify the files and code sections that need modification

### Phase 2: Design Review (MANDATORY)
Create a comprehensive implementation design and present it to the user for approval:

#### **Modification Summary**
- Which comment to address
- What to modify (summary)

#### **Detailed Modification Plan**
- **Target Files**: Specify each file and modification location
- **Specific Changes**: Code-level changes
- **New Files Required**: Files that need to be created (if any)

#### **Impact Analysis**
- Other code affected by these changes
- Test files requiring updates
- Documentation update necessity

#### **Implementation Approach**
- Chosen approach and reasoning
- Alternative approaches if any

#### **Confirmation Points**
- Points requiring user confirmation
- Unclear points or decisions needed

**⚠️ IMPORTANT**: Ask the user: "この設計で実装を進めてよろしいですか？修正点があればお知らせください。"

**Wait for user approval before proceeding to Phase 3.**

### Phase 3: Implementation (Only after approval)
1. Implement the code changes based on the approved design
2. Ensure code quality and consistency with existing codebase
3. Follow project coding standards and best practices

### Phase 4: Review Changes
1. Review all modified files
2. Verify that changes align with the design
3. Check for potential issues or missing updates

### Phase 5: Commit
1. Generate a descriptive commit message that:
   - References the PR comment
   - Summarizes the changes made
   - Follows conventional commit format if applicable
2. Stage and commit the changes
3. Push to the remote branch

## Output Format

### During Design Phase (Phase 2)
Output the design in Japanese following the structure above.

### During Implementation (Phase 3-5)
Provide progress updates for each step:
- "✅ ファイルXを修正しました"
- "✅ 変更内容を確認しました"
- "✅ コミットを作成しました: [commit message]"
- "✅ リモートブランチにプッシュしました"

### Final Summary
Provide a summary including:
- Modified files and changes made
- Commit hash and message
- Next steps (if any)

**Output to file**: Ask the user if they want to save the implementation log. If yes, save to `/tmp/pr-comment-implement-$(basename "$PR_URL" | cut -d'#' -f1 | sed 's|.*/||').md`.

## Notes
- Always prioritize user approval on the design before implementation
- If user requests design changes, revise and re-present for approval
- Use Read tool to understand existing code before making changes
- Use Edit tool for precise modifications to existing files
- Use Write tool only when creating new files
- Ensure all changes are tested if applicable
- Follow the project's git commit conventions
