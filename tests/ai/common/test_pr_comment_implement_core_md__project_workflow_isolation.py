import unittest

from support import REPO_ROOT


CORE = REPO_ROOT / "ai/common/pr_comment_implement_core.md"


class PrCommentImplementProjectWorkflowIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

    def test_project_workflow_writes_stay_inside_task_worktree(self):
        contract = self.content.index(
            "#### Constrain project-mandated workflows to the task worktree"
        )
        phase_two = self.content.index("### Phase 2: Design Review", contract)
        section = self.content[contract:phase_two]
        normalized = " ".join(section.split())

        self.assertIn(
            "At Phase 3, repository instructions may require another project workflow",
            normalized,
        )
        self.assertIn("Invoke it from `TASK_PATH` only", normalized)
        self.assertIn(
            "Every write target must remain inside `TASK_PATH`",
            normalized,
        )
        self.assertIn(
            "stay on `TASK_BRANCH` without creating another worktree",
            normalized,
        )

    def test_external_workflow_target_stops_before_write_and_implementation(self):
        normalized = " ".join(self.content.split())

        self.assertIn(
            "stop before that write and before implementation",
            normalized,
        )
        self.assertIn(
            "including a planning directory under `ORIGINAL_PATH`",
            self.content,
        )
        self.assertIn("Do not silently skip the required workflow", self.content)
        self.assertIn(
            "read-only initialization as satisfying it",
            self.content,
        )

    def test_codex_generated_skill_carries_isolation_contract(self):
        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")
        codex_normalized = " ".join(codex_skill.split())

        self.assertIn(
            "#### Constrain project-mandated workflows to the task worktree",
            codex_normalized,
        )
        self.assertIn(
            "Every write target must remain inside `TASK_PATH`",
            codex_normalized,
        )


if __name__ == "__main__":
    unittest.main()
