Respond in **Japanese**. For each finding:

```markdown
**[path/to/file.ext:line]** テスト品質 (信頼度: XX)
- **カテゴリ**: カバレッジ不足 / テスト品質 / テスト設計 / 境界値テスト欠如 / モック不適切
- **問題**: 何が不十分か
- **不足しているテストケース**: 具体的に何をテストすべきか
- **修正案**: テストの追加または改善方法
```

If none qualify, output:
`テスト品質: 信頼度75以上の問題は見つかりませんでした。`
