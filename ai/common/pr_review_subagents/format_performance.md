Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** パフォーマンス (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: N+1クエリ / 不要なIO / アルゴリズム計算量 / 過剰なアロケーション / キャッシュ欠如 / ホットパスのブロッキング
- **問題**: 何が性能上問題か
- **発生条件**: どの経路・頻度・データ規模で顕在化するか
- **修正案**: 具体的な改善方法
```

If none qualify, output:
`パフォーマンス: 信頼度75以上のパフォーマンス問題は見つかりませんでした。`
