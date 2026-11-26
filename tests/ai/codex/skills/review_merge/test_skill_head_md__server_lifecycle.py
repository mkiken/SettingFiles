import unittest

from support import REPO_ROOT


class ReviewMergeServerLifecycleTest(unittest.TestCase):
    def test_herdr_startup_and_generated_skill_contract(self):
        head = (REPO_ROOT / "ai/codex/skills/review-merge/skill_head.md").read_text()
        generated = (REPO_ROOT / "ai/codex/skills/review-merge/SKILL.md").read_text()
        generation = (REPO_ROOT / ".claude/skills/ai-prompt-generation/references/generation.md").read_text()

        for requirement in (
            "HERDR_ENV=1",
            "/api/info",
            "resolved `<RUN_DIR>`",
            "no-focus Herdr tab",
            "exec python3 ~/.config/ai-pr/bin/serve_review_report.py",
            "independently fetch the report URL in a later tool call",
            "close only the tab created for this attempt",
            "Outside Herdr, use the core fallback",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, head)
        self.assertIn(head, generated)
        self.assertIn("Codex uses a Herdr tab for server startup", generation)


if __name__ == "__main__":
    unittest.main()
