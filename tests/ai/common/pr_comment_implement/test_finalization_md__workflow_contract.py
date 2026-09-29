import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/pr_comment_implement/finalization.md"


class FinalizationWorkflowContractTest(unittest.TestCase):
    def test_finalization_keeps_action_and_cleanup_boundaries(self):
        content = PATH.read_text(encoding="utf-8")
        for required in (
            "### Phase 5: Pre-Action Preparation",
            "### Phase 6: Unified Action Selection",
            'add "コミットのみ"',
            'always add "コミットしない"',
            "### Abort or decline cleanup",
            "### Verify the final reaction state",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)

    def test_push_uses_verified_merge_head(self):
        content = PATH.read_text(encoding="utf-8")
        for required in (
            'EXPECTED_PUSH_HEAD=$(git -C "$ORIGINAL_PATH" rev-parse HEAD)',
            'if [ "$CURRENT_PUSH_HEAD" != "$EXPECTED_PUSH_HEAD" ]; then',
            'git push origin "${EXPECTED_PUSH_HEAD}:refs/heads/${HEAD_BRANCH}"',
            'git log "${PRE_COMMIT_HEAD}..${EXPECTED_PUSH_HEAD}"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)


if __name__ == "__main__":
    unittest.main()
