import unittest

from support import REPO_ROOT


class WorktreeAuthorizationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(encoding="utf-8")
        cls.section = content.split("# Cross-Repository Work\n", 1)[1].split(
            "\n# Instruction File vs. Code Drift", 1
        )[0]

    def test_task_worktree_permission_is_independent_of_skill_and_location(self):
        self.assertIn(
            "Creating a worktree for the requested task and performing task-scoped "
            "work inside it require no additional permission, regardless of skill use "
            "or whether the worktree is outside the session project.",
            self.section,
        )
        self.assertIn(
            "Display the resolved path and proceed; normal Git bookkeeping required "
            "to create and use the worktree is included.",
            self.section,
        )

    def test_other_external_writes_and_workflow_gates_still_require_authorization(self):
        self.assertIn(
            "Obtain permission before dangerous operations affecting anything outside "
            "that worktree, such as discarding another worktree's changes or rewriting "
            "shared branch history.",
            self.section,
        )
        self.assertIn(
            "display the exact target and obtain confirmation before mutating it, "
            "unless the user explicitly named that external target.",
            self.section,
        )
        self.assertIn(
            "This exception does not authorize other external write targets or bypass "
            "existing plan-mode, design-approval, deletion, commit, push, or "
            "PR-action gates.",
            self.section,
        )

    def test_temporary_data_exception_checks_resolved_location_and_cleanup(self):
        for requirement in (
            "Task-scoped temporary data under `/tmp` require no external-write approval",
            "even when a workflow confines writes to its task worktree",
            "Resolve symlinks in the target and existing parent directories first",
            "beneath the resolved `/tmp` root (including `/private/tmp` on macOS)",
            "A symlink escaping that root retains the existing approval requirements",
            "Clean up session-created temporary data at completion using the Temp File Cleanup rules",
            "other workflow gates remain in force",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.section)


class CommitConfirmationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(
            encoding="utf-8"
        )
        cls.workflow = content.split("# Post-Implementation Workflow\n", 1)[1]

    def test_push_sets_and_verifies_upstream(self):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(encoding="utf-8")
        self.assertIn("Immediately before `git push -u`, resolve the current branch", content)
        self.assertIn("push that branch with `-u`", content)
        self.assertIn("verify its remote ref and configured upstream match the pushed branch", content)

    def test_commit_still_requires_user_choice(self):
        self.assertIn("inspect the working tree, then ask whether", self.workflow)
        self.assertIn(
            "to commit and push, commit only, or leave changes uncommitted",
            self.workflow,
        )
        self.assertIn("Perform the selected git action", self.workflow)

    def test_fixed_menu_is_limited_to_claude_and_gemini(self):
        # Codex Default mode prohibits a multiple-choice permission question;
        # retain the existing fixed menu only for the other two platforms.
        menu = self.workflow.split("For Claude and Gemini, present exactly:", 1)[1]
        menu = menu.split("\n\nStage only", 1)[0]
        labels = [line for line in menu.splitlines() if line[:1].isdigit()]
        self.assertEqual(len(labels), 3)
        for label in ("コミットしてプッシュ", "コミットのみ", "コミットしない"):
            self.assertIn(label, menu)


if __name__ == "__main__":
    unittest.main()
