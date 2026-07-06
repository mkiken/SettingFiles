### Aggregate

1. Drop "no findings" messages from final findings, but count them as zero in the summary.
2. Remove inter-agent duplicates by same root cause at the same file/line; keep the clearest/highest-confidence finding.
3. Recheck existing comments NDJSON. Skip an unresolved duplicate when same path within ±5 lines and same root cause, or same target symbol/concept fixable by the same change, with duplicate confidence >= 70. Do not skip resolved or outdated comments; if they overlap, re-report and mention the past resolved comment in the detail. Collect skipped findings for `[既コメント済]`.
4. Route findings agents marked `[既存コード]` (critical pre-existing issues) to `## 既存コードに関する指摘`, keeping the critical category noted in the detail line.
5. Route all other test-related findings to `## テストに関する指摘`, regardless of source agent. Decide pre-existing-vs-changed first: a `[既存コード]` finding about tests still goes to `## 既存コードに関する指摘`.
6. If a bug and missing test share the same root cause, keep the bug as the finding and mention the test gap only as supporting detail unless a distinct test change is required.
7. Output only actionable findings requiring a concrete response. No praise, compliance confirmations, or non-actionable observations.
8. Reclassify by confidence: High 90-100, Medium 75-89, Low only when explicitly notable below threshold.
9. Every final finding needs `[path:line]` or `[path:~line]`; drop findings without line references. Verify every surviving anchor against the head-revision file (read-only file inspection in local mode) — sub-agents may mistakenly report diff-text positions; correct mismatches or downgrade to `~line`.
10. Number findings sequentially across regular, test, and pre-existing-code sections. Omit empty sections and omit `## レビュー注目ポイント` unless it adds concrete unresolved actions not already numbered.
11. If no actionable findings remain, output only `対応が必要な指摘はありません。`
12. If any finding was skipped as an existing-comment duplicate, add `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line each:
    `- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>`

### Final Format

Respond entirely in Japanese. Every finding must be header, indented detail bullet, then `---` separator, including the last finding.

Header forms:

- `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約`
- `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約（重大カテゴリ）` (used only inside `## 既存コードに関する指摘`)

Use this structure and omit empty sections:

```markdown
## レビューサマリー

| 領域 | 指摘数 | 最高信頼度 |
| ---- | ------ | ---------- |
| バグ検出 | N | XX |
| セキュリティ | N | XX |
| アーキテクチャ | N | XX |
| エラーハンドリング | N | XX |
| Git履歴 | N | XX |
| テスト品質 | N | XX |

## 🔴 High Priority（信頼度90-100）

1. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority（信頼度75-89）

2. （同形式）

## 🟢 Low Priority（特筆すべきもの）

3. （同形式）

## テストに関する指摘

### 🟡 Medium Priority（信頼度75-89）

4. （同形式、領域はテスト品質）

## 既存コードに関する指摘

### 🔴 High Priority（信頼度90-100）

5. （同形式、要約末尾に重大カテゴリ）

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```
