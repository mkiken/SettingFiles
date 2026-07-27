### Scope

If a test target is given, apply this workflow to it directly. If the target is ambiguous or missing, ask the user to clarify using `ask_user` before proceeding.

Where the workflow above says "the platform's confirmation primitive," use `ask_user`; for Phase 4's multi-select review, list the verdict options and let the user pick multiple by number or name.
