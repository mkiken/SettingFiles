import re
import unittest

from support import REPO_ROOT


CORE_PATH = REPO_ROOT / "ai/common/review_post_core.md"
MERGE_CORE_PATH = REPO_ROOT / "ai/common/review_merge_core.md"
MECHANICS_PATH = REPO_ROOT / "ai/common/pr_post_mechanics_core.md"
RENDERER_PATH = REPO_ROOT / "shell/common/pr/generate_review_report.py"
CLAUDE_SKILL_PATH = REPO_ROOT / "ai/claude/skills/review-post/SKILL.md"
CODEX_SKILL_PATH = REPO_ROOT / "ai/codex/skills/review-post/SKILL.md"

# (carryover値, 絵文字, ラベル) — 絵文字はcore mdから実バイトをコピーする。
# 手打ちするとVS16(U+FE0F)欠落で偽陰性になる。
CARRYOVER_LABELS = (
    ("skipped_before", "⏭️", "前回スキップ"),
    ("should_be_fixed", "❓", "前回対応済のはず"),
    ("fixed_before", "🔁", "前回修正済み（再指摘）"),
    ("fix_skipped_before", "⏸️", "前回修正スキップ"),
    ("fix_rejected_before", "❌", "前回修正却下"),
)


class ReviewPostCarryoverLineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = CORE_PATH.read_text(encoding="utf-8")
        cls.merge_core = MERGE_CORE_PATH.read_text(encoding="utf-8")
        cls.mechanics = MECHANICS_PATH.read_text(encoding="utf-8")
        cls.renderer = RENDERER_PATH.read_text(encoding="utf-8")

    def test_all_carryover_values_map_to_expected_label(self):
        for value, emoji, label in CARRYOVER_LABELS:
            expected = f'. == "{value}" then "_前回対応状況: {emoji} {label}_"'
            with self.subTest(value=value):
                self.assertIn(expected, self.core)

    def test_unknown_carryover_value_fails_closed(self):
        self.assertIn('else error("unknown carryover value")', self.core)

    def test_missing_or_empty_carryover_yields_no_line(self):
        for required in (
            '.carryover // ""',
            "absent, `null`, or an empty string yields an empty",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_carryover_line_precedes_attribution_as_final_line(self):
        for required in (
            "immediately followed by `expected_attribution` as the final line",
            "no blank line between them",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_preflight_rejects_mismatched_or_stray_carryover_line(self):
        for required in (
            "the second-to-last line differs from",
            "the body contains `_前回対応状況:` at all",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_preview_index_appends_carryover_marker_from_same_source(self):
        for required in (
            "⟨{絵文字} {ラベル}⟩",
            "the preview and the posted body can never disagree",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_carryover_distinct_from_head_commit_already_addressed_check(self):
        self.assertIn(
            'unrelated to the head-commit "already addressed" check',
            self.core,
        )

    def test_labels_match_renderer_carry_map(self):
        # レンダラのCARRYラベルとcore mdの日本語ラベルが食い違うと、
        # HTMLバッジとPRコメントで同じcarryoverが別の文言で表示される。
        for _, _, label in CARRYOVER_LABELS:
            with self.subTest(label=label):
                self.assertIn(label, self.renderer)
                self.assertIn(label, self.core)

    def test_carryover_emoji_avoid_decision_button_emoji(self):
        # 🚫/🔧はreport.htmlのdecisionボタンとdecision-statusで使用中
        # (generate_review_report.py内 "対応する"/"対応しない")。
        # priority絵文字(🔴🟡🟢)ともpost側で衝突するため、
        # carryover絵文字はこの集合に含めない。
        forbidden = {"🔧", "🚫", "🔴", "🟡", "🟢"}
        used = {emoji for _, emoji, _ in CARRYOVER_LABELS}
        self.assertTrue(forbidden.isdisjoint(used))

    def test_mechanics_core_has_no_carryover_vocabulary(self):
        # pr_post_mechanics_core.mdはreview-postとpr-comment-postの共有コア。
        # pr-comment-postはGitHubコメントを読み merged.json を持たないため、
        # run-dir固有語彙のcarryoverをここに置けない。
        self.assertNotIn("carryover", self.mechanics)
        self.assertNotIn("前回対応状況", self.mechanics)

    def test_claude_runtime_and_generated_codex_skill_receive_the_contract(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        codex_skill = CODEX_SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("review_post_core.md", claude_skill)
        self.assertIn(self.core, codex_skill)

    def test_carryover_value_count_matches_merge_core_declaration(self):
        # review_merge_core.mdの正典行が宣言する値数とpost側の分岐数が
        # 食い違うと、merge側に値が追加されてもpost側の更新漏れを
        # ラベル照合だけでは検出できない。
        canonical_line = next(
            line
            for line in self.merge_core.splitlines()
            if line.startswith("`line_spec` keeps the original notation")
        )
        declared_values = re.findall(r'"([a-z_]+)"', canonical_line)
        declared_values = [v for v in declared_values if v != "null"]
        self.assertEqual(len(declared_values), len(CARRYOVER_LABELS))


if __name__ == "__main__":
    unittest.main()
