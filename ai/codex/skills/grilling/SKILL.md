---
name: grilling
description: Relentless design-tree interview that resolves a plan's decisions in dependency order, asking each round's answerable questions together with a recommended answer for every one. Use when the user asks to grill a plan, stress-test thinking before building, or work through a design's open decisions — including Japanese phrasing such as "詰めて", "尋問して", "設計を固めて".
---

# Grilling

Interview the user relentlessly until you reach a shared understanding. Map the plan as a **design tree**: every decision branches into the decisions that hang off it.

Adapted from Matt Pocock's `grilling` skill (MIT, github.com/mattpocock/skills), rewritten for this runtime's confirmation primitive and plan handling.

Run inline in this session — do not fork a subagent for the interview itself. Only dispatch a `worker` to settle a *fact* (see Facts vs. Decisions below); a worker cannot spawn its own subagent (max depth 1).

## The Frontier

The **frontier** is every decision whose prerequisites are already settled: the questions you can ask *now* without guessing at answers you have not heard yet.

Ask the whole frontier in one round. Each answer reshapes the tree — settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round.

A question whose answer depends on another question still open in this round belongs to a *later* round, not this one. This ordering is the whole point: it is what keeps you from asking the user to decide something they cannot yet decide.

## Recommended Answers

Every question carries your recommended answer. Not a neutral menu — your actual pick, with the reason it beats the alternatives. A user who is unsure can start from your recommendation instead of stalling; that is what moves a design forward.

Base recommendations on the codebase and on `AGENTS.md` / `CLAUDE.md` conventions, not on generic best practice.

## Facts vs. Decisions

Finding **facts** is your job, never the user's. When a frontier question needs a fact from the environment — what a file contains, how an API behaves, whether a dependency exists — dispatch a `worker` to find it. Never ask the user for anything you could look up yourself.

Do not block on it. A running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the worker to report; ask the rest of the frontier now.

The **decisions** are the user's. Put each to them and wait.

## Asking a Round

Prefer `request_user_input` when the round's option count fits the tool's limit, passing each authored label exactly once — do not count the client's auto-provided free-form `Other` as an authored option. If a round's options exceed the limit, ask in plain text as a Markdown ordered list starting from `1.`; a number-only reply selects that option.

- Put the question's substance in the question text itself — the mechanism, the trade-off, the consequence of each branch. Option labels are too short to carry it.
- Mark the recommended option's label with `(推奨)` and lead with it.
- Give every option concrete pros/cons; when they do not fit the label, append them as `— Pros: … / Cons: …`.
- Never ask open-ended questions — always concrete choices.

## Recording Decisions

After each round, output the plan text with the round's decisions folded in — this response is the persistence mechanism; there is no plan file to write back to (Codex has no `~/.codex/plans`, and the plan lives only as `<proposed_plan>` content). The next round, and the next `<proposed_plan>`, must build on this updated text, not the original.

Include a `## Decisions` table in that text:

```markdown
| Decision | Choice | Why this over the alternatives | Depends on |
|----------|--------|-------------------------------|------------|
```

The `Depends on` column names the earlier decisions that unblocked this one — that is the design tree, made durable.

## Finishing

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed.

Then state plainly what remains genuinely undecided and why, and confirm with the user that you have reached a shared understanding. Do not act on the plan until they confirm.
