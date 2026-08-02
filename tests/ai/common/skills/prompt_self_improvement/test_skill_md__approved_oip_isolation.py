import unittest

from support import REPO_ROOT


SKILL_PATH = REPO_ROOT / "ai/common/skills/prompt-self-improvement/SKILL.md"


class ApprovedOipIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = " ".join(SKILL_PATH.read_text(encoding="utf-8").split())

    def test_approved_proposals_never_modify_the_source_worktree(self):
        for required in (
            "### Apply approved proposals in isolation",
            "require its source worktree to be clean with an attached branch",
            "Never edit that source worktree directly",
            "When `$worktree-task` is available",
            "run the complete isolated workflow in a newly created branch and worktree",
            "Do not reuse a removed task worktree, deleted branch, or an unrelated existing worktree",
            "retain the workflow's commit, merge, cleanup, and push confirmations",
            "When `$worktree-task` is unavailable, use another already-validated isolated worktree workflow",
            "stop without editing SettingFiles",
            "Never fall back to changing the source worktree directly",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)


if __name__ == "__main__":
    unittest.main()
