import unittest

from support import REPO_ROOT


STANCE = "Assume the change is broken somewhere"
GUARD = "if you cannot break it, report no finding"
DIMENSIONS = ("bugs", "claims", "design", "history", "performance", "security", "tests")


class ReviewerDefectStanceTest(unittest.TestCase):
    def test_every_platform_rules_common_has_stance_and_guard(self):
        for platform in ("claude", "gemini", "codex"):
            with self.subTest(platform=platform):
                rules = (REPO_ROOT / "ai" / platform / "agents_src/rules_common.md").read_text(encoding="utf-8")
                self.assertIn(STANCE, rules)
                self.assertIn(GUARD, rules)

    def test_generated_specialists_carry_stance(self):
        for platform in ("claude", "gemini", "codex"):
            for dimension in DIMENSIONS:
                name = f"pr_reviewer_{dimension}.toml" if platform == "codex" else f"pr-reviewer-{dimension}.md"
                with self.subTest(platform=platform, dimension=dimension):
                    content = (REPO_ROOT / "ai" / platform / "agents" / name).read_text(encoding="utf-8")
                    self.assertIn(STANCE, content)


if __name__ == "__main__":
    unittest.main()
