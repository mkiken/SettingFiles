### Output Format

Respond entirely in Japanese.

**Priority mapping (影響度 × 信頼度)** — self-assessed per finding. 影響度: High = data loss/outage/vulnerability/broad breakage, Medium = limited malfunction or degradation, Low = minor. 信頼度 = 0–100 certainty that the issue is real. Priority: High = 影響度High & 信頼度>=75; Medium = 影響度Medium & 信頼度>=75, or 影響度High & 信頼度<75 (append 「要検証」 to the detail); Low = 影響度Low & notable, or 影響度Medium & 信頼度<75 (append 「要検証」). The mapping decides priority only, never whether a finding is reported — the calling skill's actionability rules decide that.

Each finding MUST use this exact three-part structure:

- **Header line**: `N. **[file:line]** 領域 (影響度: XX / 信頼度: XX): 短い一行の要約` — path relative to repository root, `[path:line]` for a single line or `[path:startLine-endLine]` for a range; 領域 is a Japanese area label from the calling skill's dimension list. Inside `## 既存コードに関する指摘`, append `（重大カテゴリ）` to the summary.
- **Detail line**: `   - Full explanation and recommendation (indented sub-bullet)`. Do not cram the explanation into the header line.
- **Separator line**: `---` after every finding, including the last one — a hard structural requirement that must never be omitted.

Number findings sequentially across all sections — never restart numbering per section.

Use this skeleton, omitting empty sections and empty priority levels. The calling skill may prepend extra leading sections (e.g. a summary table) before the first priority section:

```markdown
## 🔴 High Priority（影響度High・信頼度75+）

1. **[path/to/file.ext:line]** 領域 (影響度: XX / 信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority

2. （同形式）

## 🟢 Low Priority

3. （同形式）

## テストに関する指摘

### 🟡 Medium Priority

4. （同形式、領域はテスト品質）

## 既存コードに関する指摘

### 🔴 High Priority（影響度High・信頼度75+）

5. （同形式、要約末尾に重大カテゴリ）

## [既コメント済] スキップした指摘

- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```

Place `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line per skipped finding as shown; omit the section when nothing was skipped. `## 総合評価` states the merge verdict line plus a short overall comment.

If no actionable findings remain after deduplication, output only (no skeleton, no 総合評価):

```markdown
対応が必要な指摘はありません。
```
