# Claude Plan Review

The always-on prompt has already established that both review gates hold.
Output the plan file's complete current content as ordinary assistant text in
the same turn, without a code fence or summary, before showing the choice. The
later `ExitPlanMode` rendering is intentionally separate.

Use one single-select `AskUserQuestion` with exactly these four options:

- Both: open the browser and also run the deep-dive.
- Deep-dive only: run grilling then dig without opening the browser.
- Open the browser now, decide on the deep-dive after reading.
- Neither.

The deep-dive is one fixed pair. Never offer grilling and dig separately.
Complete grilling until its frontier is empty and the user confirms shared
understanding; only then run dig on grilling's resulting plan.

For Both, open the browser first. For the deferred browser option, wait for the
user to finish reading without calling `ExitPlanMode`, then ask whether to run
the whole pair or proceed. Both skills read the plan file fresh. Grilling runs
inline so its questions reach the user. If dig returns analysis from a fork,
conduct its confirmation rounds in the main session.

After dig rewrites the plan, repeat the complete presentation and choice flow
once, after dig and not between stages. Stop ephemeral viewers after review,
but never stop the persistent port-4649 viewer.

For browser review, read `references/browser.md`. A plan-mode plan file uses a
persistent server rooted at `~/.claude/plans`: probe
`http://127.0.0.1:4649/__mdv/assets/mdv.css`, start
`mdv -d -n -q -p 4649 ~/.claude/plans` only if the probe fails, and parse its
printed URL because a collision may move it to a higher, ephemeral port. Open
the target file directly under that URL. Never stop the true port-4649 server;
stop a collision-created ephemeral instance after review.
