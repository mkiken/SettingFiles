import unittest

from support import REPO_ROOT

WORKTREE_TASK_TOML = REPO_ROOT / "ai/gemini/commands/worktree-task.toml"


class WorktreeTaskTomlContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = WORKTREE_TASK_TOML.read_text(encoding="utf-8")

    def test_file_exists(self):
        self.assertTrue(WORKTREE_TASK_TOML.is_file())

    def test_uses_args_placeholder(self):
        self.assertIn("{{args}}", self.content)

    def test_includes_ask_user_instruction(self):
        self.assertIn("ask_user", self.content)

    def test_includes_run_shell_command_instruction(self):
        self.assertIn("run_shell_command", self.content)

    def test_references_shared_worktree_task_core(self):
        self.assertIn(
            "!{cat ~/.gemini/common/shared_skills/worktree-task/SKILL.md}",
            self.content,
        )


if __name__ == "__main__":
    unittest.main()
