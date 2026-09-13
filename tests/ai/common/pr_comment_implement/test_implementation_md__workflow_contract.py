import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/pr_comment_implement/implementation.md"


class ImplementationWorkflowContractTest(unittest.TestCase):
    def test_implementation_requires_approval_and_handles_no_code_change(self):
        content = PATH.read_text(encoding="utf-8")
        self.assertIn("### Phase 3: Implementation (Only after approval)", content)
        self.assertIn("### Phase 4: Review Changes", content)
        self.assertIn("do not edit files or create an empty commit", content)
        self.assertNotIn("### Phase 5: Pre-Action Preparation", content)


if __name__ == "__main__":
    unittest.main()
