import unittest

from support import REPO_ROOT


HEAD = REPO_ROOT / "ai/codex/skills/pr-comment-review/skill_head.md"
GENERATED = REPO_ROOT / "ai/codex/skills/pr-comment-review/SKILL.md"


class PrCommentReviewDescriptionScopeTest(unittest.TestCase):
    def test_description_routes_analysis_away_from_implementation(self):
        for path in (HEAD, GENERATED):
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertIn("Analyze a specific GitHub PR comment URL", content)
                self.assertIn("without implementing the requested change", content)


if __name__ == "__main__":
    unittest.main()
