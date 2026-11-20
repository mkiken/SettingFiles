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
            "to create and use the worktree is included, as is safely removing "
            "(`git worktree remove`, `git branch -d`) a worktree or branch this task "
            "created once it is proven unchanged.",
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
            "existing plan-mode, design-approval, other deletion, commit, push, or "
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
            "Clean up session-created temporary data at completion using the `task-completion` skill's Temp File Cleanup rules",
            "other workflow gates remain in force",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.section)

    def test_worktree_cleanup_rules_pin_provenance_and_confirmation(self):
        for requirement in (
            "only when direct evidence shows this session created it",
            "treat uncertain provenance as not AI-created",
            "remove it without asking via `git worktree remove` (no `--force`) and `git branch -d`",
            "no uncommitted changes and no commits unmerged into the original branch",
            "If it is not clean, report what remains and ask first",
            "When the user asked for the worktree, ask before removing it, unless the active skill defines its own automatic cleanup",
            "a worktree this session did not create to be unneeded, you may ask whether to delete it; never delete it without confirmation",
            "Never use `--force` or `git branch -D` without explicit confirmation",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.section)

    def test_task_completion_skill_runs_worktree_cleanup(self):
        skill = (REPO_ROOT / "ai/common/skills/task-completion/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Temp File Cleanup, then Worktree Cleanup, then", skill)
        self.assertIn("## Worktree Cleanup\n", skill)


class CommitConfirmationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/common/skills/task-completion/SKILL.md").read_text(
            encoding="utf-8"
        )
        workflow = content.split("## Post-Implementation Workflow\n", 1)[1]
        cls.workflow = workflow.split("\n## Opportunistic", 1)[0]

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

    def test_commit_choice_displays_resolved_push_destination(self):
        choice = self.workflow.split("For Claude and Gemini, present exactly:", 1)[0]
        for requirement in (
            "Before asking, display the current branch, push remote, and destination branch",
            "mark any unresolved value as unknown instead of guessing",
            "do not infer the destination branch from the upstream when the planned push uses the current branch name",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, choice)

    def test_fixed_menu_is_limited_to_claude_and_gemini(self):
        # Codex Default mode prohibits a multiple-choice permission question;
        # retain the existing fixed menu only for the other two platforms.
        menu = self.workflow.split("For Claude and Gemini, present exactly:", 1)[1]
        menu = menu.split("\n\nStage only", 1)[0]
        labels = [line for line in menu.splitlines() if line[:1].isdigit()]
        self.assertEqual(len(labels), 3)
        for label in ("コミットしてプッシュ", "コミットのみ", "コミットしない"):
            self.assertIn(label, menu)


class PrFindingsHandoffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (REPO_ROOT / "ai/common/skills/task-completion/SKILL.md").read_text(
            encoding="utf-8"
        )
        cls.section = cls.skill.split("## PR Findings Handoff\n", 1)[1].split(
            "\n## Opportunistic", 1
        )[0]

    def test_runs_between_post_implementation_and_improvement_check(self):
        self.assertIn(
            "the Post-Implementation Workflow, then PR Findings Handoff, then the Opportunistic",
            self.skill,
        )

    def test_section_pins_ownership_check_and_write_paths(self):
        for requirement in (
            "gh api user --jq .login",
            "gh pr edit",
            "gh pr comment",
            "`PR本文に追記する` / `修正する` / `記載しない`",
            "`コメント投稿する` / `修正する` / `投稿しない`",
            "Codex follows its `# User Confirmation` rules",
            "even if a PR skill already asked",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.section)

    def test_section_skips_reviews(self):
        self.assertIn(
            "the results are a review (any review skill or ad-hoc review), with or without findings",
            self.section,
        )

    def test_prompt_base_loads_task_completion_for_pr_results(self):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(encoding="utf-8")
        section = content.split("# Task Completion\n", 1)[1]
        self.assertIn("the PR findings handoff", section)
        self.assertIn(
            "any turn that delivers verification or investigation results for a specific GitHub PR",
            section,
        )


if __name__ == "__main__":
    unittest.main()
