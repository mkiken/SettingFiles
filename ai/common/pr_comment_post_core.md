## Goal

Post selected numbered findings from a previous `pr-review` result as one GitHub Pull Request Review, confirmed once, submitted together when possible.

## Workflow

1. Build an internal numbered index from the previous `pr-review` output. Its serial numbers are the source of truth: preserve them exactly and never reorder or renumber, across regular priority sections, `## テストに関する指摘`, and `## 既存コードに関する指摘` (single continuous numbering; never restart at 1).
   - Format: `N. [path/to/file.ext:line] Priority | Category: 概要`, where `N` is the original serial number. The review header is `N. **[path:line]** 領域 (影響度: XX / 信頼度: XX): 概要` — use the 領域 label as `Category` and the surrounding priority section heading as `Priority`; never copy the `(影響度: XX / 信頼度: XX)` parenthetical into posted comment bodies.
   - If `ITEM_NUMBERS` is empty, show the available numbered items and ask which to post; otherwise do not display the index.
2. Parse `ITEM_NUMBERS` as space- or comma-separated original serial numbers.
3. For each requested number, copy that index entry's `file_path`, `line_spec`, `priority`, `category`, and full description verbatim — never reconstruct or infer an item's content from its number. If a number has no matching entry, stop and report the mismatch instead of substituting another item.
   - Priority emoji: High `🔴`, Medium `🟡`, Low `🟢`.
   - Items anchored `[path:~line]` (pre-existing code outside the diff) cannot be inline comments: exclude them from the Review API `comments` array and post each via the no-file/line `gh pr comment` fallback, prefixing the body with `**[path:~line]**`.

Then follow the posting mechanics below.
