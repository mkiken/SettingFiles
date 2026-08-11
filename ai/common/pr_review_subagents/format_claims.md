Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** 主張検証 (影響度: High|Medium|Low / 信頼度: XX)
- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff
- **カテゴリ**: 説明と差分の不一致 / 修正主張だが根本原因未対応 / テスト済み主張だがテスト変更なし / 挙動・互換性主張の誤り / スコープ外変更の混入
- **主張**: PRの主張の引用と出典（PR body / コミットSHA / linked issue）
- **実際**: 差分が実際に行っていること
- **修正案**: 主張と実装のどちらをどう直すか
```

If none qualify, output:
`主張検証: 信頼度75以上の問題は見つかりませんでした。`
