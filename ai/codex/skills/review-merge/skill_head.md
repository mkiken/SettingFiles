---
name: review-merge
description: >
  Merge multi-AI PR review results into merged.json and an HTML report. Accepts
  a run directory; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

For the report server, run `serve_review_report.py` without `--open`. In Herdr (`HERDR_ENV=1`), replace the core's `nohup` startup with this procedure:

1. Check `<RUN_DIR>/.server.json` and request `/api/info` on its port. Reuse its URL only if the response identifies the resolved `<RUN_DIR>`; a missing, stale, or mismatched server needs startup.
2. Start a no-focus Herdr tab in the current workspace, using the tab creation response's pane ID. Run `exec python3 ~/.config/ai-pr/bin/serve_review_report.py <RUN_DIR>` in that pane, shell-quoting the resolved run directory. The foreground server keeps the tab alive and `exec` closes it when the server exits. Do not close a running report tab.
3. Read the URL from `<RUN_DIR>/.server.json`, verify `/api/info` identifies the resolved run directory and independently fetch the report URL in a later tool call. If startup or verification fails, close only the tab created for this attempt and report the failure; do not open an unverified URL. Open the verified URL once.

Outside Herdr, use the core fallback and independently fetch its returned URL before opening it once in the browser.

Before rendering, compare every `sources[].text` in `merged.json` against its original finding, including all indented detail and proposed fixes through the separator. Confirm each finding appears exactly once; repair any missing or truncated text and repeat the comparison before proceeding.
