---
name: second-opinion
description: Ask another AI CLI (codex, claude, gemini) for a second opinion. User-invoked, or proposed (confirm first) when stuck, wanting another view, or another AI should weigh in.
---

# Second Opinion

Consult another AI CLI non-interactively, read-only, and report its answer. The other AI's answer is evidence, not a verdict: weigh it against your own view and let the user decide. This skill never edits files; delegating edits is a separate job (the official `/codex:rescue`, or the CLIs directly).

Arguments, if any, follow the skill name:

`<codex|claude|gemini>[,...] [--model <m>] [--effort <e>] [--critique] [--review|--debug|--plan] [--background] <question>`

- Never call the CLI you are running in. If the target is omitted, ask which of the other two to use.
- `--critique` also hands over your own answer for the other AI to attack. The default is independent: the question, facts, and unverified points only, so the other AI is not anchored by you.
- `--review`, `--debug`, `--plan` select a role contract from `references/brief.md`. With none, the brief is neutral.

## 1. Launch gate

When the user invoked this skill, go straight to the model/effort check below. When you decided on your own that a second opinion would help, you may only propose it, in one of these situations: you are stuck or the judgment is hard, a different viewpoint would help, or another AI should weigh in. Ask at most once per topic; if declined, do not propose it again.

Ask through the platform's confirmation mechanism and run no CLI until the answer arrives. The confirmation shows: target(s), role, independent or critique, foreground or background, the reason, and for each target the proposed model and effort.

Model and effort change answer quality and cost a lot, so always pass both explicitly; never rely on a CLI default. Read `references/models.md` for the candidates and difficulty-based defaults. If `--model` or `--effort` is missing, propose values in this same confirmation, even for a user-invoked run. Gemini has no effort setting: pass the model only and show "effort: not settable" in the confirmation.

## 2. Gather context

Find the files the question depends on, following callers and related tests. The other AI cannot see this conversation, so any log, command output, or trace it needs must be real: re-run the command into a temp file instead of retyping from memory, and keep each command so it can be re-run later. Do not paste the contents of large files; list their paths and the other AI reads them (read-only access to the working tree is enough).

Sort what you know into three piles: the question, facts you verified (each with a `file:line` or an output file), and points you have not verified.

## 3. Write the brief

Read `references/brief.md` and fill its template into a `mktemp` file with a quoted heredoc and the terminator `__SECOND_OPINION_END__`, so the shell expands nothing and code samples cannot cut it short. Keep question, facts, and unverified points in their own blocks. In independent mode, state the user's question faithfully: no conclusions, hypotheses, or proposed solutions of your own. End the brief with the no-delegation rule from the template.

## 4. Run

Pick a session ID before the run so the conversation can be resumed. Pass the brief on stdin, write stdout and stderr to separate files, and replace the placeholders with the confirmed values.

| target | command | model | effort | session |
|---|---|---|---|---|
| codex | `codex exec -s read-only --skip-git-repo-check --json -o <answer_file> -` | `-m <model>` | `-c 'model_reasoning_effort="<e>"'` | `thread_id` in the first `--json` event on stdout |
| gemini | `gemini -p "Follow the instructions on stdin." --approval-mode plan` | `-m <model>` | not settable | `--session-id <uuid>` (unverified) |
| claude | `claude -p --permission-mode plan` | `--model <model>` | `--effort <level>` | `--session-id <uuid>` |

- Codex writes its final message only to `<answer_file>`; stdout carries the JSON events. For claude and gemini, stdout is the answer.
- Never add `--ephemeral` or `--no-session-persistence`: they make resuming impossible.
- Several targets: start each CLI in the background of one shell command with its own output files, then `wait`.
- Use the longest foreground tool timeout; for runs expected to take longer, or with `--background`, use the platform's background execution if it has one, otherwise run normally and say so.

Failure means any of: non-zero exit, an empty answer, or no `__END_OF_ANSWER__` line at the end. On failure show the key stderr lines and stop. Treat partial output as not an answer: do not summarize it as one (if shown, label it "incomplete, not an answer"), do not answer in its place, and do not add flags such as `--skip-trust` or looser sandbox settings to get past an error.

## 5. Context request

If the answer ends with a `## Context request`, collect the requested artifacts or the user's clarification and resume the same session once per target with a follow-up that holds only the new material:

- claude: `claude -p --permission-mode plan --model <model> --effort <level> --resume <id>`
- codex: `codex exec resume <id> --skip-git-repo-check -c 'sandbox_mode="read-only"' -m <model> -c 'model_reasoning_effort="<e>"' -o <answer_file> -` (`resume` takes no `-s`)
- gemini: `--resume` (unverified)

Ask for more only once per target. If a request remains after the follow-up, report it as unresolved. If the session ID is missing or resuming fails, say so and start a fresh call that includes the previous answer.

## 6. Report

Present the answer unaltered in substance: keep what the other AI marked as fact, inference, uncertainty, and its confidence. Before reporting a specific finding, open the cited `file:line` yourself and label the finding verified or unverified. Then give where it agrees and disagrees with your own view; with several targets, add a combined conclusion (agreements, disagreements, the takeaway).

Per target, also report: model, effort, session ID, the resume command, and the evidence (`file:line` references plus the command that regenerates each attached output). Then stop. Make no code changes and apply no suggested fix until the user chooses which ones to apply.

## 7. Clean up

Delete the brief and output temp files you created with `trash`; the regeneration commands in the report keep the evidence.
