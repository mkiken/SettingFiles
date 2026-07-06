Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** バグ検出 (信頼度: XX)
- **カテゴリ**: ロジックエラー / null参照 / レース条件 / off-by-one / API誤用 / リソースリーク
- **問題**: 何が問題か
- **再現シナリオ**: どのような入力や条件で発生するか
- **修正案**: 具体的な修正方法
```

If none qualify, output:
`バグ検出: 信頼度75以上の問題は見つかりませんでした。`
