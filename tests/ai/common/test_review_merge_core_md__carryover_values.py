import unittest

from support import REPO_ROOT


CORE_PATH = REPO_ROOT / "ai/common/review_merge_core.md"
CODEX_SKILL_PATH = REPO_ROOT / "ai/codex/skills/review-merge/SKILL.md"
CLAUDE_SKILL_PATH = REPO_ROOT / "ai/claude/skills/review-merge/SKILL.md"
RENDERER_PATH = REPO_ROOT / "shell/common/pr/generate_review_report.py"

CARRYOVER_VALUES = (
    "skipped_before",
    "should_be_fixed",
    "fixed_before",
    "fix_skipped_before",
    "fix_rejected_before",
)


class ReviewMergeCarryoverValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = CORE_PATH.read_text(encoding="utf-8")

    def test_all_carryover_values_declared_in_core(self):
        for value in CARRYOVER_VALUES:
            with self.subTest(value=value):
                self.assertIn(f'"{value}"', self.core)

    def test_renderer_carry_map_matches_core_value_set(self):
        # コアmdの値マッピングとレンダラのCARRYラベルが食い違うと、
        # merged.jsonに書かれたcarryover値がHTML上で生文字列フォールバック表示になる。
        renderer = RENDERER_PATH.read_text(encoding="utf-8")
        for value in CARRYOVER_VALUES:
            with self.subTest(value=value):
                self.assertIn(f"{value}:", renderer)

    def test_claude_runtime_and_generated_codex_skill_receive_the_contract(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        codex_skill = CODEX_SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("review_merge_core.md", claude_skill)
        self.assertIn(self.core, codex_skill)


if __name__ == "__main__":
    unittest.main()
