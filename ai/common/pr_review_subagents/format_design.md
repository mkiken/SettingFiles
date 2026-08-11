Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** 設計品質 (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: 関心の分離 / 結合度 / 凝集度 / APIデザイン / スケーラビリティ / 既存ユーティリティの再実装 / 命名・イディオムの乖離 / 規約からの逸脱 / 冗長・重複 / 過剰な抽象化 / 複雑なロジック
- **問題**: 何が構造・一貫性・複雑さの面で問題か
- **比較対象/現状**: 一貫性系は参照した既存コードのパス（可能なら行番号）と慣例、簡素化系は現状コードの要点、構造系は放置した場合の影響（保守性・拡張性）
- **修正案**: 具体的な改善方法（簡素化系は簡素化後のスケッチと動作が変わらない理由）
```

If none qualify, output:
`設計品質: 信頼度75以上の問題は見つかりませんでした。`
