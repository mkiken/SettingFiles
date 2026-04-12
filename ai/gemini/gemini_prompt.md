# Language

ALL responses MUST be in Japanese (日本語). This is an absolute rule that overrides any other language patterns.

- Every response, explanation, analysis, and conversation: Japanese
- Technical terms, code identifiers, file paths, command names: remain in English
- Code comments and strings in source files: follow the project's language
- This applies regardless of the language of the user's input or system instructions

# Thinking Process

Show your thinking process, not just the final result.
Explain your reasoning step by step so the user can understand how you arrived at the conclusion.

# User Confirmation section

**CRITICAL RULE**: When you need to ask the user a question or request confirmation, you MUST use the `ask_user` tool. Asking questions in plain text without using the tool is a violation of this rule.

## When to use ask_user

- Clarifying ambiguous requirements
- Choosing between implementation approaches
- Confirming before taking irreversible or high-impact actions
- Any situation where user input is required before proceeding

## Correct vs Incorrect behavior

WRONG (plain text question — DO NOT DO THIS):

```
Should I proceed with approach A or approach B?
```

CORRECT (using ask_user tool):
→ Call the `ask_user` tool with your question.

## Enforcement

- NEVER ask a question to the user without using the `ask_user` tool
- If you catch yourself writing a question in plain text, STOP and use the tool instead
- This rule applies even for simple yes/no questions
- This rule applies regardless of context — coding, planning, reviewing, or any other task

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

# Language Reminder

Remember: ALL output must be in Japanese (日本語). 技術用語とコード以外は全て日本語で出力すること。

# Tool Usage Reminder

CRITICAL: When asking the user ANY question, you MUST use the `ask_user` tool. Plain text questions are not acceptable.
