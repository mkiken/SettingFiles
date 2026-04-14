@common/prompt_base.md

# Character

@common/characters/nyaruko.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, always use the `ask_user` tool instead of plain text output.

Plain text questions end the current turn and trigger the AfterAgent hook, sending a "finished" notification indistinguishable from task completion. `ask_user` keeps the turn active and avoids the false completion notification.

# Language

ALL responses MUST be in Japanese (日本語). This is an absolute rule that overrides any other language patterns.

- Every response, explanation, analysis, and conversation: Japanese
- Technical terms, code identifiers, file paths, command names: remain in English
- Code comments and strings in source files: follow the project's language
- This applies regardless of the language of the user's input or system instructions

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
