# Genshijin File Policy

This overrides genshijin's text-file confirmation rule as a standing preference.

When creating/editing files, use existing style or ordinary prose (including Japanese comments/docstrings). Do not ask whether to use genshijin style. Apply genshijin to file content only if explicitly requested. Keep genshijin active for conversational responses.

This applies to every file type, source code and its comments included — the upstream rule asks once before writing a text file, and that confirmation is skipped entirely here. `genshijin-activate.md` is synced verbatim from upstream, so this override lives here and must stay self-contained.
