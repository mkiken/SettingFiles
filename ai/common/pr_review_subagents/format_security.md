Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** セキュリティ (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: インジェクション / 認証/認可 / データ露出 / 暗号化 / SSRF / 依存関係
- **問題**: 何が脆弱か
- **攻撃ベクトル**: 具体的な悪用シナリオ
- **修正案**: 具体的な修正方法
```

If none qualify, output:
`セキュリティ: 信頼度75以上の脆弱性は見つかりませんでした。`
