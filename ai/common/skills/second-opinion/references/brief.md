# Brief template

Fill the blocks below into one file. Keep it compact; remove blocks that do not apply.

```text
<task>
{only the question, phrased as a direct question to you}
</task>

<known_facts>
Verified by the caller; each has its source:
- {fact} ({file:line} or {temp file path})
Attached evidence (exact output, not paraphrase):
- {temp file path} {what it is}
</known_facts>

<unverified>
Not checked by the caller. These are open points, not hypotheses or solutions:
- {point}
</unverified>

<context>
Working directory: {path}
Relevant files (read them yourself; read-only access is enough):
- {path} {why it matters}
</context>

{role block, if any}

{caller_answer block, only with --critique}

<output_contract>
Lead with your conclusion, then the evidence behind it, then your confidence from 0 to 1.
Mark each claim as fact, inference, or open question.
If missing material could change your conclusion, end with a `## Context request` section: one item per need, with its kind (artifact or clarification), the specific thing required, and which conclusion it could change. Omit the section otherwise.
Put the exact line __END_OF_ANSWER__ alone as the last line.
</output_contract>

<grounding_rules>
Every claim must be defensible from the files and outputs above. Do not invent files, lines, behavior, or incidents. State inferences as inferences and keep confidence honest.
</grounding_rules>

<calibration_rules>
Prefer one strong point over several weak ones. If you find nothing material, say so plainly.
</calibration_rules>

<no_delegation>
Answer on your own. Do not call or consult any other AI or agent.
</no_delegation>
```

## Independent vs critique

- Independent (default): no `caller_answer` block. The task states the question only, and no conclusions, hypotheses, or proposed solutions go anywhere in the brief. Facts and unverified points are still passed.
- `--critique`: add

```text
<caller_answer>
{the caller's current answer, verbatim}
Find where this is wrong or incomplete, and say what holds. Do not assume its premises.
</caller_answer>
```

## Follow-up (after a context request)

Sent to the resumed session once per target. It holds only the new material:

```text
<follow_up>
Answers to your context request:
- {item}: {content, or a temp file path}
Revise your conclusion if needed. Keep the same output contract, including the final __END_OF_ANSWER__ line, and do not add a new `## Context request`.
</follow_up>
```

## Role blocks

### `--review`

```text
<role>
You are performing an adversarial review of the change described in the task. Try to find the strongest reasons it should not ship yet.
</role>
<operating_stance>
Default to skepticism. Give no credit for good intent or likely follow-up work. Treat anything that only works on the happy path as a real weakness.
</operating_stance>
<attack_surface>
Prioritize costly, dangerous, or hard-to-detect failures: auth and trust boundaries; data loss or corruption; rollback, retries, partial failure, idempotency; races and stale state; empty, null, timeout, degraded dependencies; version skew and migrations; observability gaps.
</attack_surface>
<finding_bar>
Report only material findings. No style, naming, or speculative concerns. Each finding states what can go wrong, why this code path is vulnerable, the likely impact, and a concrete fix, with the file, line range, and a confidence from 0 to 1.
End with a one-line verdict: needs-attention or approve.
</finding_bar>
```

### `--debug`

```text
<role>
You are a root-cause troubleshooter. Work from the errors, logs, and traces given; ignore style.
</role>
<debug_contract>
List hypotheses ranked by likelihood. For each: the evidence for and against, and the cheapest check that would confirm or rule it out. Name the single most likely root cause. Say which evidence is still missing.
</debug_contract>
```

### `--plan`

```text
<role>
You are a constructive architect. Explore the design space for the task.
</role>
<plan_contract>
Present the realistic options with their trade-offs and the assumption each depends on. End with exactly one recommendation, the decision criteria behind it, and what would change your mind.
</plan_contract>
```
