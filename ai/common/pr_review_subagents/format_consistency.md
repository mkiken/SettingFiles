Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** 一貫性 (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: 既存ユーティリティの再実装 / 命名の乖離 / 構造・イディオムの乖離 / 確立された規約からの逸脱
- **問題**: 何が既存コードと乖離しているか
- **比較対象**: 参照した類似既存コードのパス（可能なら行番号）と、そこで確立されている慣例
- **修正案**: 既存の慣例に合わせる具体的な方法
```

If none qualify, output:
`一貫性: 信頼度75以上の一貫性の問題は見つかりませんでした。`
