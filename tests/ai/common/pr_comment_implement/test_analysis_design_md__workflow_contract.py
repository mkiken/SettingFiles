import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/pr_comment_implement/analysis-design.md"


class AnalysisDesignWorkflowContractTest(unittest.TestCase):
    def test_analysis_reaches_one_design_gate_without_implementation(self):
        content = PATH.read_text(encoding="utf-8")
        self.assertIn("### Phase 1: Analysis", content)
        self.assertIn("### Decide whether the comment should be acted on (MANDATORY)", content)
        self.assertIn("### Phase 2: Design Review (MANDATORY)", content)
        self.assertIn("### Executable boundary in plan mode", content)
        self.assertIn("skip the\n🚀 reaction POST and worktree creation", content)
        self.assertIn("After approval, the implementer posts the deferred reaction", content)
        self.assertIn("#### Refresh a changed PR head before implementation", content)
        self.assertIn("git merge --ff-only \"$HEAD_BRANCH\"", content)
        self.assertIn("re-present Phase 2 and wait for approval", content)
        self.assertNotIn("### Phase 3: Implementation", content)

    def test_changes_view_review_comment_fragment_is_classified_as_thread(self):
        content = PATH.read_text(encoding="utf-8")
        row = next(line for line in content.splitlines() if line.startswith("| `#discussion_r(\\d+)`"))
        self.assertIn("`#r(\\d+)`", row)
        self.assertIn("REPLY_PATH=thread", row)

    def test_task_worktree_boundary_allows_only_shared_temporary_data_exception(self):
        content = PATH.read_text(encoding="utf-8")
        section = content.split(
            "#### Constrain project-mandated workflows to the task worktree", 1
        )[1].split("### Phase 2:", 1)[0]
        for requirement in (
            "Every write target must remain inside\n`TASK_PATH`, except task-scoped temporary data",
            "Cross-Repository Work `/tmp` exception; those writes need no additional\napproval",
            "The workflow must stay on `TASK_BRANCH` without creating another\nworktree",
            "that is not covered by\nthat temporary-data exception, stop before that write",
            "Report the exact external target",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, section)


if __name__ == "__main__":
    unittest.main()
