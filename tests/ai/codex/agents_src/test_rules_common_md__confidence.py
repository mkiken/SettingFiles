import unittest

from support import REPO_ROOT


RULES = REPO_ROOT / "ai/codex/agents_src/rules_common.md"
CLAUDE_RULES = REPO_ROOT / "ai/claude/agents_src/rules_common.md"
GEMINI_RULES = REPO_ROOT / "ai/gemini/agents_src/rules_common.md"


class ReviewerConfidenceContractTest(unittest.TestCase):
    def test_codex_keeps_actionable_low_confidence_findings(self):
        rules = RULES.read_text(encoding="utf-8")
        self.assertIn("all actionable findings", rules)
        self.assertIn("below 75", rules)
        self.assertIn("要検証", rules)
        self.assertNotIn("confidence >= 75", rules)

    def test_other_platform_thresholds_stay_at_75(self):
        for path in (CLAUDE_RULES, GEMINI_RULES):
            with self.subTest(path=path):
                self.assertIn("confidence >= 75", path.read_text(encoding="utf-8"))

    def test_generated_specialists_keep_platform_rules(self):
        for platform, marker in (("codex", "要検証"), ("gemini", "confidence >= 75"), ("claude", "confidence >= 75")):
            for dimension in ("bugs", "claims", "design", "history", "performance", "security", "tests"):
                name = f"pr_reviewer_{dimension}.toml" if platform == "codex" else f"pr-reviewer-{dimension}.md"
                with self.subTest(platform=platform, dimension=dimension):
                    content = (REPO_ROOT / "ai" / platform / "agents" / name).read_text(encoding="utf-8")
                    self.assertIn(marker, content)
                    self.assertIn("該当する問題は見つかりませんでした。", content)


if __name__ == "__main__":
    unittest.main()
