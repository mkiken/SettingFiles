### Phase 3: Implementation (Only after approval)

Work only inside `TASK_PATH`. Never edit `ORIGINAL_PATH`.

Implement only the approved scope. When the change alters observable behavior
that no existing test pins, add or update a test that pins it; when an
existing test already pins the new behavior, keep it as the proof and add
none. Run the narrowest useful verification command; broaden only when the
touched surface is shared or high risk.

When `NO_CODE_CHANGE=true`, do not edit files or create an empty commit.
Preserve the concrete findings and verification results for the reply body,
then continue to Phase 4.

### Phase 4: Review Changes

Confirm the diff matches the design; check for missing tests or side effects.
Run these from `TASK_PATH`:

```bash
git diff --check
git diff
git status --short
```

When `NO_CODE_CHANGE=true`, confirm that the task introduced no file changes
and report any pre-existing or unrelated changes separately.
