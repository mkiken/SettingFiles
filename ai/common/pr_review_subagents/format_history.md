Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** Git履歴 (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: リグレッション / パターン違反 / 繰り返しフィードバック / 高チャーン / 最近の修正への影響
- **問題**: 何が懸念されるか
- **根拠**: 裏付けとなるコミットハッシュまたはPR番号
- **修正案**: 具体的な対処方法
```

影響度: High = data loss/outage/vulnerability/broad breakage, Medium = limited malfunction or degradation, Low = minor. 信頼度 = 0–100 certainty that the issue is real.

If none qualify, output:
`Git履歴: 該当する問題は見つかりませんでした。`
