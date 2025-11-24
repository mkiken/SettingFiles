# Completion Notification

Send notifications to indicate task completion or waiting state.

## When to Send Notifications

Send a notification when **ANY** of these conditions are met:

1. **Response is complete and waiting for next user input:**
   - You have finished answering a question
   - You have completed explaining something
   - You have finished showing results or analysis
   - Your current task is done and no further action is planned

2. **Explicitly waiting for user decision:**
   - Awaiting command execution approval
   - Requesting content confirmation before file operations
   - Asking user to choose between options
   - Waiting for additional information needed to proceed

3. **Long-running operation has completed:**
   - Build, test, or compilation finished
   - Search or analysis completed
   - File operations completed

## When NOT to Send Notifications

Do NOT send notifications in these cases:

1. **Mid-process situations:**
   - While still analyzing or thinking
   - Showing intermediate results with more to come
   - In the middle of a multi-step explanation
   - Processing a complex task with multiple parts pending

2. **Immediate continuation expected:**
   - After showing code and about to explain it
   - After one search result and planning to search more
   - During a back-and-forth clarification within the same task

## Decision Rule

**Simple test**: Ask yourself:
- "Am I done with my turn and expecting the user to respond?"
  → YES = Send notification
- "Am I still in the middle of working on something?"
  → NO = Don't send notification

## Notification Command
```bash
terminal-notifier -title "Gemini" \
 -message "(summary of what was done or what is needed)" \
 -sound "Purr" \
 -execute "open -a Ghostty" \
 -ignoreDnD
```

## Important Notes
- When in doubt, prefer sending a notification (false positive is better than missing one)
- The notification should be sent AFTER your complete response, not during
- Replace '(summary of what was done or what is needed)' with a brief description in Japanese

# ═══════════════════════════════════════════════════
# SuperGemini Framework Components
# ═══════════════════════════════════════════════════

# Core Framework
@BUSINESS_PANEL_EXAMPLES.md
@BUSINESS_SYMBOLS.md
@FLAGS.md
@PRINCIPLES.md
@RESEARCH_CONFIG.md
@RULES.md

# Behavioral Modes
@MODE_Brainstorming.md
@MODE_Introspection.md
@MODE_Task_Management.md
@MODE_Token_Efficiency.md
