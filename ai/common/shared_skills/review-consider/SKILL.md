---
name: review-consider
description: Discuss merged PR review findings marked for AI consideration and record agreed policies. Accepts an optional run directory; defaults to the current PR's latest run.
---

# Review Consider

Respond in Japanese. The optional first argument is the run directory. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number`, then run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`. Resolve the run directory to an absolute path. Do not accept item numbers.

Read `merged.json` and browser-owned `state.json`; use merged.json `pr_number` as <PR_NUMBER>. Require schema version 2, exact item ID agreement, decisions from `fix`, `post`, `consider`, `dismiss`, or null, and string notes when present. Select only items with `decision: "consider"`; use their optional `note`. If none are selected, report that and stop. Invalid or missing state stops the workflow; ask the user to save the report again. Never write `state.json` or `merged.json`.

Read `consider/consider_state.json` if present. Require schema version 1, matching resolved `run_dir`, a `head_ref_oid` matching merged.json and the current PR head (`gh pr view <PR_NUMBER> --json headRefOid --jq .headRefOid`), and item keys drawn from merged.json. If invalid, stale, or the head cannot be verified, stop and ask for a new review run; never overwrite existing results. Before starting a new result, also require merged.json's head to equal the current PR head. Preserve all existing items on updates.

For each selected item, inspect its sources, note, and relevant code. Discuss validity, alternatives, impact and a recommended policy. Ask for missing information and do not rush agreement. Do not edit code or post to GitHub. Record the reasoning and proposed policy as `draft` while discussion continues. Set `approved` only after the user confirms that item's policy and, if present, its exact posting text. A changed policy or posting text returns the item to `draft` until confirmed again. Do not use subagents.

Write `consider/consider_state.json` with this shape, retaining other items:

```json
{
  "schema_version": 1,
  "run_dir": "/absolute/run/path",
  "head_ref_oid": "reviewed PR head SHA",
  "items": {
    "1": {"status": "draft", "rationale": "evidence and trade-offs", "policy": "proposed or agreed policy", "post_body": null}
  }
}
```

`status` is `draft` or `approved`; `rationale` and `policy` are strings; `post_body` is null or the agreed finding body string, without attribution or carryover suffixes. Write valid JSON atomically. Explain that the user must reopen the report, select fix, post, or dismiss, and save before running the corresponding existing skill.
