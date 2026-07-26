Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** 簡素化 (影響度: Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: 冗長なコード / 重複ロジック / 過剰な抽象化 / 深いネスト / 不要な分岐 / 複雑な条件式
- **現状**: 現在のコードの要点（簡潔な抜粋またはスケッチ）
- **提案**: 簡素化後のコードのスケッチと、動作が変わらない理由
```

If none qualify, output:
`簡素化: 信頼度75以上の簡素化提案は見つかりませんでした。`
