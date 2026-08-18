Post selected review items from a merge run directory to the PR as review comments. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items (`id. [file:line_spec] priority | area: summary`) and ask the user which ids to post.
3. If a selected id has no matching item, or state.json ids do not exist in merged.json (stale state), stop and report the mismatch instead of guessing.
4. Build the posting index from the selected items: `N. [file:line_spec] Priority | 領域: 概要` where `N` = item id, Priority from `priority` (high→High, medium→Medium, low→Low), 領域 from `area`, 概要 from `summary`. When `expected_carryover` is non-empty, append ` ⟨{絵文字} {ラベル}⟩` — the same emoji and label as `expected_carryover`, without its surrounding underscores or the `前回対応状況: ` prefix — so the preview and the posted body can never disagree. The 概要 comparison in the posting mechanics ignores this appended carryover marker.
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

   - Derive the carryover line from `carryover` in merged.json with this exact mapping. Build `expected_carryover` using `jq`; never translate, abbreviate, or invent a label:

```bash
expected_carryover=$(jq -r --argjson item_id "$item_id" '
  .items[] | select(.id == $item_id) | .carryover // "" |
  if . == "" then ""
  elif . == "skipped_before" then "_前回対応状況: ⏭️ 前回スキップ_"
  elif . == "should_be_fixed" then "_前回対応状況: ❓ 前回対応済のはず_"
  elif . == "fixed_before" then "_前回対応状況: 🔁 前回修正済み（再指摘）_"
  elif . == "fix_skipped_before" then "_前回対応状況: ⏸️ 前回修正スキップ_"
  elif . == "fix_rejected_before" then "_前回対応状況: ❌ 前回修正却下_"
  else error("unknown carryover value")
  end
' "$run_dir/merged.json") || exit 1
```

   - `carryover` absent, `null`, or an empty string yields an empty `expected_carryover` and no carryover line. An unrecognized value fails the `jq` call; stop and report it instead of posting the raw value. This is the previous run's decision/fix outcome for the same finding, unrelated to the head-commit "already addressed" check in the posting mechanics.
   - The posted description body is: the merged `summary`, a blank line, the normalized detail text, a blank line, then `expected_carryover` (only when non-empty) immediately followed by `expected_attribution` as the final line — the two underscore lines are adjacent, with no blank line between them. Always emit the attribution line, including single-source items.
   - Before confirmation and before every post request, reject the body if it contains `## レビューサマリー`, the summary-table header `| 領域 | 指摘数 | 最高信頼度 |`, or a final line different from `expected_attribution`. Also reject it when `expected_carryover` is non-empty and the second-to-last line differs from `expected_carryover`, or when `expected_carryover` is empty and the body contains `_前回対応状況:` at all. Stop without posting on failure. This rejects `_指摘元: C_`, a hand-written carryover label, and any other abbreviated or mismatched line.
   - Retain each selected item id while constructing its comment payload. Before the Review API request, reject the payload unless its item ids have the same count and exact set as the selected ids: each selected id must appear exactly once, with no extras. A zero-length payload for non-empty selection, any duplicate, or any mismatch stops before posting; do not rely on a successful API response to detect a dropped item.
5. `head_ref_oid` in merged.json is the review-time head commit for the re-anchoring check in the posting mechanics below. Items whose `line_spec` starts with `~` are pre-existing-code anchors and cannot be inline comments (see the fallback rule in the mechanics). That prefix is only one reason an item cannot be inline: a plain line number can also fall outside the diff hunks, so decide inline eligibility with the diff-hunk check in the mechanics rather than the prefix alone.

Then follow the posting mechanics below.
