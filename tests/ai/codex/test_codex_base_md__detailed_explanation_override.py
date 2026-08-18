import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"
AGENTS_PATH = REPO_ROOT / "ai/codex/_AGENTS.md"


class CavemanDefaultStyleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = CODEX_BASE_PATH.read_text(encoding="utf-8")
        cls.agents = AGENTS_PATH.read_text(encoding="utf-8")

    def test_codex_base_uses_caveman_as_the_default_conversation_style(self):
        for required in (
            "installed `caveman` skill",
            "`full` intensity",
            "Load its current `SKILL.md` instead of duplicating its rules here.",
            "`/caveman off` or `normal mode` disables it.",
            "Persisted files, code, comments, commits, documentation, and third-party messages",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_generated_agents_applies_the_caveman_default_style(self):
        directive = "Use the installed `caveman` skill"

        self.assertIn(directive, self.agents)
        self.assertNotIn("原始人のように簡潔に返答せよ", self.agents)


if __name__ == "__main__":
    unittest.main()
