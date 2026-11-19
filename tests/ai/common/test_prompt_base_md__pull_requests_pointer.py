import unittest

from support import REPO_ROOT

SOURCES = (
    REPO_ROOT / "ai/common/prompt_base.md",
    REPO_ROOT / "ai/codex/_AGENTS.md",
)


class PullRequestsPointerTest(unittest.TestCase):
    def test_pointer_names_the_pr_skills(self):
        for path in SOURCES:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertIn("# Pull Requests", content)
                self.assertIn("`pr-create-by-branch` skill", content)

    def test_pr_rules_are_not_always_loaded(self):
        # PR rules live in pr_body_format.md so sessions that never create a PR
        # do not pay for them; keep them out of the always-on prompt.
        for path in SOURCES:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("# Task-Based Pull Requests", content)
                self.assertNotIn("# PR Review Focus Points", content)


if __name__ == "__main__":
    unittest.main()
