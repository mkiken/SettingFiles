Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** エラーハンドリング (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: サイレント失敗 / エラーメッセージ不足 / エッジケース欠如 / エラー伝播 / フォールバック欠如
- **問題**: 何が不十分か
- **ユーザー影響**: エンドユーザーまたは開発者にどのような影響があるか
- **修正案**: 具体的な改善方法
```

If none qualify, output:
`エラーハンドリング: 信頼度75以上の問題は見つかりませんでした。`
