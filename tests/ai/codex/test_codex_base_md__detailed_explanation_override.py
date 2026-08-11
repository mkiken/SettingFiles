import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"
AGENTS_PATH = REPO_ROOT / "ai/codex/_AGENTS.md"


class DetailedExplanationOverrideTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = CODEX_BASE_PATH.read_text(encoding="utf-8")
        cls.agents = AGENTS_PATH.read_text(encoding="utf-8")

    def test_explicit_detail_requests_suspend_genshijin_for_one_response(self):
        for required in (
            "explicitly asks for a detailed explanation",
            "more detail, clarity, background, rationale, or step-by-step instructions",
            "suspend genshijin style for that response",
            "Use ordinary Japanese prose",
            "Resume genshijin style on the next response",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_generated_agents_applies_the_codex_override_after_genshijin(self):
        override = "explicitly asks for a detailed explanation"

        self.assertIn("原始人のように簡潔に返答せよ", self.agents)
        self.assertIn(override, self.agents)
        self.assertLess(self.agents.index("原始人のように簡潔に返答せよ"), self.agents.index(override))


if __name__ == "__main__":
    unittest.main()
