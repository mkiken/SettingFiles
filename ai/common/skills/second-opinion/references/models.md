# Model and effort candidates

Always pass an explicit model and effort. These are proposals for the confirmation step; the user may change them. Model names go stale, so check the repository aliases (`shell/zsh/alias/ai/codex.zsh`, `gemini.zsh`) when they look out of date.

| target | model candidates | effort |
|---|---|---|
| codex | `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6.1-terra`, `gpt-6-luna` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh` |
| claude | `opus`, `sonnet`, `fable`, `haiku` | `low`, `medium`, `high`, `xhigh`, `max` |
| gemini | `pro`, `flash` | not settable (no CLI flag found) |

Gemini is unverified: the CLI failed to authenticate in the test environment (IneligibleTierError), so its flags, `--session-id`, and `--resume` have not been run. Report any error as is.

The codex effort values come from a third-party README; only `low` has been run. If the CLI rejects a value, report the error and ask for another.

## Default proposals by difficulty

| difficulty | proposal |
|---|---|
| routine check, quick view | codex `gpt-6.1-sol` + `medium`; claude `sonnet` + `medium`; gemini `flash` |
| hard bug, design judgment, review before shipping | codex `gpt-6.1-sol` + `high`; claude `opus` + `high`; gemini `pro` |
| highest stakes only | add `xhigh`; mention that cost and time rise sharply |

Say in the confirmation which difficulty you assumed and why.
