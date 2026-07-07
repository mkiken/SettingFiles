Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** 履歴リスク (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: リグレッション / パターン違反 / 繰り返しフィードバック / 高チャーン / 最近の修正への影響
- **問題**: 何が懸念されるか
- **根拠**: 裏付けとなるコミットハッシュまたはPR番号
- **修正案**: 具体的な対処方法
```

If none qualify, output:
`Git履歴: 信頼度75以上のリグレッションリスクは見つかりませんでした。`
