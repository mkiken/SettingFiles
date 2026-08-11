Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** バグ検出 (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: ロジックエラー / null参照 / レース条件 / off-by-one / API誤用 / リソースリーク / サイレント失敗 / エラーメッセージ不足 / エラー伝播・フォールバック欠如
- **問題**: 何が問題か
- **再現シナリオ**: どのような入力・条件・エラー経路で発生するか
- **修正案**: 具体的な修正方法
```

If none qualify, output:
`バグ検出: 信頼度75以上の問題は見つかりませんでした。`
