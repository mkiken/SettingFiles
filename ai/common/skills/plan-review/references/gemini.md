# Gemini Plan Review

The always-on prompt has already established that the plan meets its browser
review criteria. Ask through Gemini's user-confirmation mechanism whether to
render it. If declined, continue the normal plan flow.

If accepted, use the existing plan artifact when it has a real file path;
otherwise write the complete plan to a session-owned scratchpad directory.
Tell the user which file to review, read `references/browser.md`, and use its
small-directory flow. Wait for the user to finish before stopping the viewer
or continuing approval. Clean up only a scratchpad created for this review.
