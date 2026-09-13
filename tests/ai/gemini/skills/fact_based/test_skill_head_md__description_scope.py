import unittest

from support import REPO_ROOT


HEAD = REPO_ROOT / "ai/gemini/skills/fact-based/skill_head.md"
GENERATED = REPO_ROOT / "ai/gemini/skills/fact-based/SKILL.md"


class FactBasedDescriptionScopeTest(unittest.TestCase):
    def test_generated_description_matches_the_scoped_source(self):
        for path in (HEAD, GENERATED):
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertIn("Verify external facts with sources", content)
                self.assertIn("not for local codebase investigation", content)


if __name__ == "__main__":
    unittest.main()
