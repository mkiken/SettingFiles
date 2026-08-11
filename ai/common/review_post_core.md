Post selected review items from a merge run directory to the PR as review comments. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items (`id. [file:line_spec] priority | area: summary`) and ask the user which ids to post.
3. If a selected id has no matching item, or state.json ids do not exist in merged.json (stale state), stop and report the mismatch instead of guessing.
4. Build the posting index from the selected items: `N. [file:line_spec] Priority | 領域: 概要` where `N` = item id, Priority from `priority` (high→High, medium→Medium, low→Low), 領域 from `area`, 概要 from `summary`.
   - Before using the most confident source's detail `text`, inspect it for a report-level summary. If the text starts with the exact heading `## レビューサマリー`, remove that heading and every following line through the line before the next H2 heading. Retain the next H2 heading and all later text. If `## レビューサマリー` appears anywhere else, or no next H2 heading exists, stop before confirmation and report the unrecognized source-text shape; never guess a deletion boundary.
   - This normalization applies only to the inline or individual-fallback finding body. Keep the merged one-line `summary` and the top-level 1–3 sentence review summary required by the posting mechanics.
   - Derive the attribution from every `sources[].ai` in merged.json order with this exact mapping. Build `expected_attribution` using `jq`; do not abbreviate, capitalize heuristically, or infer names:

```bash
expected_attribution=$(jq -r --argjson item_id "$item_id" '
  .items[] | select(.id == $item_id) |
  [.sources[].ai |
    if . == "claude" then "Claude"
    elif . == "gemini" then "Gemini"
    elif . == "codex" then "Codex"
    else error("unknown review source AI")
    end
  ] | "_指摘元: " + join(", ") + "_"
' "$run_dir/merged.json") || exit 1
```

   - The posted description body is: the merged `summary`, a blank line, the normalized detail text, a blank line, then `expected_attribution` as its final line. Always emit this line, including single-source items.
   - Before confirmation and before every post request, reject the body if it contains `## レビューサマリー`, the summary-table header `| 領域 | 指摘数 | 最高信頼度 |`, or a final line different from `expected_attribution`. Stop without posting on failure. This rejects `_指摘元: C_` and any other abbreviated or mismatched attribution.
5. `head_ref_oid` in merged.json is the review-time head commit for the re-anchoring check in the posting mechanics below. Items whose `line_spec` starts with `~` are pre-existing-code anchors and cannot be inline comments (see the fallback rule in the mechanics). That prefix is only one reason an item cannot be inline: a plain line number can also fall outside the diff hunks, so decide inline eligibility with the diff-hunk check in the mechanics rather than the prefix alone.

Then follow the posting mechanics below.
