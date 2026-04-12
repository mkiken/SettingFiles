# Design & Planning section

When creating design plans, present a minimal proposal first. Do not add extra return values, unnecessary steps, or additional log locations beyond what's strictly needed. Wait for user confirmation before expanding scope.

## Workflow section

When the user provides incremental requirements or interrupts during planning, pause and incorporate all feedback before proceeding. Do not rush to finalize.

## User Confirmation section

When you need to ask the user a question or request confirmation, always use the AskUserQuestion tool. Do not ask questions in plain text only. This applies to:

- Clarifying ambiguous requirements
- Choosing between implementation approaches
- Confirming before taking irreversible or high-impact actions

Do NOT use AskUserQuestion for plan mode acceptance. In plan mode, use ExitPlanMode to present the plan and rely on its native accept/reject mechanism.
