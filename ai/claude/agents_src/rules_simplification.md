## Rules

- Provided: PR metadata, full diff, line-numbered diff, existing comments NDJSON; do not re-fetch them.
- Changed code is primary; read surrounding context only to confirm a proposal preserves behavior exactly (change how, never what).
- Propose only clear wins: the simpler version must be obviously easier to read and maintain. Skip marginal rewrites, clever one-liners, and line-count golf. Report at most the 5 most valuable proposals.
- These are suggestions, not defects: use 影響度 Low by default, Medium only when the complexity actively obscures the change's behavior, never High. 信頼度 is your certainty that the rewrite is behavior-preserving and clearly better.
- Do not report unchanged pre-existing code; propose simplifications only for code this PR adds or modifies.
