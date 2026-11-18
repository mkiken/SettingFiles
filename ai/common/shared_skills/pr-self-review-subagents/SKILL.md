---
name: pr-self-review-subagents
description: Self-review the current branch's PR with the seven specialist subagents of pr-review-subagents, then repair and hand off as pr-self-review does. Use for an explicit subagent self-review request.
---

# PR Self Review (Subagents)

Same workflow as `pr-self-review`, with one change: the review stage runs the
specialist subagents instead of one inline reviewer.

Resolve this skill directory's real path and read its sibling
`../pr-self-review/SKILL.md`. Follow its "Establish the target", "Repair
findings", "Confirm commit and push" and "Hand off to the existing review
workflow" sections unchanged, including its approval, verification and
commit/push confirmation rules.

## Review stage

Replace pr-self-review's one-reviewer, inline-only review and its "do not launch
specialist or verifier agents" instruction with the `pr-review-subagents` skill
of the running platform (`~/.claude/skills/pr-review-subagents/SKILL.md` or
`~/.codex/skills/pr-review-subagents/SKILL.md`; read the files it references,
since `!` includes are not expanded here). Follow its Gather Once, Launch/Spawn,
adversarial verification, Aggregate and Final Format. Use the PR, branch, base
and head OIDs recorded while establishing the target; additional request text
is review emphasis only.

Do not use pr-review-subagents' PR-number argument parsing, its
`Result File Output` section or its `/pr-comment-post` footer. The aggregated findings feed
the repair stage; the remaining ones go to the run directory as pr-self-review
describes. Subagents stay read-only; only this session edits files.
