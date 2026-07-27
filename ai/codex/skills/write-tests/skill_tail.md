### Scope

If a test target is given, apply this workflow to it directly. If the target is ambiguous or missing, ask the user to clarify (`request_user_input` if available, else plain text) before proceeding.

Where the workflow above says "the platform's confirmation primitive": for a single choice, use `request_user_input`. For Phase 4's multi-select review, `request_user_input` is not built for multi-select — present a plain-text Markdown ordered list of test cases and their default verdicts, and treat a comma-separated or ranged reply (e.g. `1,3,5-7`) as the selection.
