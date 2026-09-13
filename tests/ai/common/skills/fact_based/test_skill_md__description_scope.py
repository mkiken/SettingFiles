import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/skills/fact-based/SKILL.md"


class FactBasedDescriptionScopeTest(unittest.TestCase):
    def test_description_targets_external_facts_not_local_code(self):
        content = PATH.read_text(encoding="utf-8")
        self.assertIn("Verify external facts with sources", content)
        self.assertIn("not for local codebase investigation", content)


if __name__ == "__main__":
    unittest.main()
