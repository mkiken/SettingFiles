import unittest

from support import REPO_ROOT


HEAD = REPO_ROOT / "ai/codex/skills/pr-body/skill_head.md"
GENERATED = REPO_ROOT / "ai/codex/skills/pr-body/SKILL.md"


class PrBodyDescriptionScopeTest(unittest.TestCase):
    def test_description_targets_pull_request_body_work(self):
        for path in (HEAD, GENERATED):
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertIn("Draft or update a GitHub Pull Request body", content)
                self.assertIn("including `$pr-body`", content)


if __name__ == "__main__":
    unittest.main()
