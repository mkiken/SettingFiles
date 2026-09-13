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
        self.assertNotIn("### Phase 3: Implementation", content)


if __name__ == "__main__":
    unittest.main()
