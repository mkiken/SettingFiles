---
name: grilling
description: Relentless design-tree interview that resolves a plan's decisions in dependency order, asking each round's answerable questions together with a recommended answer for every one. Use when the user asks to grill a plan, stress-test thinking before building, or work through a design's open decisions — including Japanese phrasing such as "詰めて", "尋問して", "設計を固めて".
---

# Grilling

Interview the user relentlessly until you reach a shared understanding. Map the plan as a **design tree**: every decision branches into the decisions that hang off it.

Adapted from Matt Pocock's `grilling` skill (MIT, github.com/mattpocock/skills), rewritten for this environment's confirmation primitive and plan-file workflow.

Run inline in this session — never fork a subagent for the interview itself; a forked agent has no `AskUserQuestion` and its questions never reach the user. Only dispatch a subagent to settle a *fact* (see Facts vs. Decisions below).

## The Frontier

The **frontier** is every decision whose prerequisites are already settled: the questions you can ask *now* without guessing at answers you have not heard yet.

Ask the whole frontier in one round. Each answer reshapes the tree — settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round.

A question whose answer depends on another question still open in this round belongs to a *later* round, not this one. This ordering is the whole point: it is what keeps you from asking the user to decide something they cannot yet decide.

## Recommended Answers

Every question carries your recommended answer. Not a neutral menu — your actual pick, with the reason it beats the alternatives. A user who is unsure can start from your recommendation instead of stalling; that is what moves a design forward.

Base recommendations on the codebase and on `CLAUDE.md` / `AGENTS.md` conventions, not on generic best practice.

## Facts vs. Decisions

Finding **facts** is your job, never the user's. When a frontier question needs a fact from the environment — what a file contains, how an API behaves, whether a dependency exists — dispatch a subagent to find it. Never ask the user for anything you could look up yourself.

Do not block on it. A running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the subagent to report; ask the rest of the frontier now.

The **decisions** are the user's. Put each to them and wait.

## Asking a Round

Use `AskUserQuestion` — this environment's confirmation primitive. A plain-text question ends the turn and misfires the Stop hook's completion notification.

- The tool takes at most 4 questions per call and 2-4 options each. When a round's frontier is wider than that, split it across consecutive `AskUserQuestion` calls in the same turn rather than dropping questions or collapsing distinct decisions into one.
- Put the question's substance in the `question` field itself — the mechanism, the trade-off, the consequence of each branch. Option labels are too short to carry it, and text preceding a tool call may never reach the user.
- Mark the recommended option's label with `(推奨)` and lead with it.
- Give every option concrete pros/cons in its `description`.
- Never ask open-ended questions. The auto-provided free-form `Other` covers the answer you did not anticipate — do not author your own.

## Recording Decisions

After each round, fold the settled decisions into the plan file — the active plan under `~/.claude/plans/`, or the plan text under discussion. The conversation is not the record; a decision that lives only in chat is lost at the next compaction.

Append or update a `## Decisions` table:

```markdown
| Decision | Choice | Why this over the alternatives | Depends on |
|----------|--------|-------------------------------|------------|
```

The `Depends on` column names the earlier decisions that unblocked this one — that is the design tree, made durable.

## Finishing

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed.

Then state plainly what remains genuinely undecided and why, and confirm with the user that you have reached a shared understanding. Do not act on the plan until they confirm.
