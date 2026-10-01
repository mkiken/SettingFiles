import unittest

from support import REPO_ROOT


HEAD = REPO_ROOT / "ai/codex/skills/pr-review/skill_head.md"


class PrReviewHeadScopeTest(unittest.TestCase):
    def setUp(self):
        self.head = HEAD.read_text(encoding="utf-8")

    def test_local_mode_requires_exact_head_and_available_base(self):
        self.assertIn("baseRefOid", self.head)
        self.assertIn("headRefOid", self.head)
        self.assertIn("git rev-parse HEAD", self.head)
        self.assertIn("git cat-file -e", self.head)
        self.assertIn("all three checks", self.head)
        self.assertIn("headRefOid", self.head.split("remote mode", 1)[-1])

    def test_investigates_entire_change_and_large_diff(self):
        self.assertIn("every changed file", self.head)
        self.assertIn("callers", self.head)
        self.assertIn("related tests", self.head)
        self.assertIn("similar implementations", self.head)
        self.assertIn("Count", self.head)
        self.assertIn("100 lines", self.head)

    def test_uses_available_tools_and_scoped_scratchpad(self):
        self.assertNotIn("`Read`", self.head)
        self.assertNotIn("`Glob`", self.head)
        skill = (HEAD.parent / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("session scratchpad", skill)
        self.assertIn("Never create temp files inside the reviewed repository's working tree", skill)
        self.assertNotIn("or elsewhere", self.head)


if __name__ == "__main__":
    unittest.main()
