# Completion Notification

Send notifications to indicate task completion or waiting state.

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
