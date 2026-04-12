## User Confirmation section

When you need to ask the user a question or request confirmation, always use the AskUserQuestion tool. Do not ask questions in plain text only. This applies to:

- Clarifying ambiguous requirements
- Choosing between implementation approaches
- Confirming before taking irreversible or high-impact actions

Do NOT use AskUserQuestion for plan mode acceptance. In plan mode, use ExitPlanMode to present the plan and rely on its native accept/reject mechanism.

## Thinking Process

For non-trivial decisions (architecture choices, debugging strategy, tradeoff analysis), show your reasoning step by step.
For straightforward tasks (simple edits, direct lookups), proceed without lengthy explanation.
