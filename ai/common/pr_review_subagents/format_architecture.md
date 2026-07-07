Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** アーキテクチャ (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: 関心の分離 / 結合度 / 凝集度 / デザインパターン / APIデザイン / スケーラビリティ
- **問題**: 何が構造的に問題か
- **影響**: このまま放置した場合の影響（保守性、拡張性など）
- **修正案**: 具体的な改善方法
```

If none qualify, output:
`アーキテクチャ: 信頼度75以上の構造的問題は見つかりませんでした。`
