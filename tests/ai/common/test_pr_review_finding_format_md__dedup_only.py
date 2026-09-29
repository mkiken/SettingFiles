import unittest

from support import REPO_ROOT


FORMAT = REPO_ROOT / "ai/common/pr_review_finding_format.md"


class PrReviewDedupOnlyFormatTest(unittest.TestCase):
    def setUp(self):
        self.format = FORMAT.read_text(encoding="utf-8")

    def test_empty_and_duplicate_only_results_are_distinct(self):
        self.assertIn("no actionable findings and no duplicates", self.format)
        self.assertIn("対応が必要な指摘はありません。", self.format)
        self.assertIn("no actionable findings but duplicates", self.format)
        self.assertIn("[既コメント済]", self.format)
        self.assertIn("対応が必要な新規指摘はありません。", self.format)

    def test_existing_priority_format_remains(self):
        for section in ("High Priority", "Medium Priority", "Low Priority"):
            self.assertIn(section, self.format)

    def test_both_codex_review_skills_include_duplicate_only_rule(self):
        for skill in ("pr-review", "pr-review-subagents"):
            with self.subTest(skill=skill):
                content = (REPO_ROOT / "ai/codex/skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("対応が必要な新規指摘はありません。", content)


if __name__ == "__main__":
    unittest.main()
