Post selected review items from a merge run directory to the PR as review comments. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items (`id. [file:line_spec] priority | area: summary`) and ask the user which ids to post.
3. If a selected id has no matching item, or state.json ids do not exist in merged.json (stale state), stop and report the mismatch instead of guessing.
4. Build the posting index from the selected items: `N. [file:line_spec] Priority | 領域: 概要` where `N` = item id, Priority from `priority` (high→High, medium→Medium, low→Low), 領域 from `area`, 概要 from `summary`. The posted description body is: the merged `summary`, a blank line, the detail `text` of the most confident source, a blank line, then a final attribution line `_指摘元: <AI names>_`. The names come from every `sources[].ai` of that item, capitalized (`claude`→Claude, `gemini`→Gemini, `codex`→Codex) and joined with `, ` in the merged.json `sources` order. Always emit this line, including single-source items.
5. `head_ref_oid` in merged.json is the review-time head commit for the re-anchoring check in the posting mechanics below. Items whose `line_spec` starts with `~` are pre-existing-code anchors and cannot be inline comments (see the fallback rule in the mechanics). That prefix is only one reason an item cannot be inline: a plain line number can also fall outside the diff hunks, so decide inline eligibility with the diff-hunk check in the mechanics rather than the prefix alone.

Then follow the posting mechanics below.
