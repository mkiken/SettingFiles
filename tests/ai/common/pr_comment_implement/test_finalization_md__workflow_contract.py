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
            'git push origin "${HEAD_BRANCH}:${HEAD_BRANCH}"',
            'git log "${PRE_COMMIT_HEAD}..${EXPECTED_PUSH_HEAD}"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)

    def test_offers_full_pr_body_flow_only_after_verified_push(self):
        content = " ".join(PATH.read_text(encoding="utf-8").split())
        for required in (
            "### Offer a PR body update",
            "the selected action contains `& push`, and the push was verified",
            "`PR bodyを更新する` / `更新しない`",
            "read `<PR_BODY_DOCS>` (adapter-defined)",
            "Confirmation Flow in full",
            "`--color=always` colored diff",
            "`### 変更点の概要`",
            "Never ask to apply a body from a summary alone.",
            "- ✅ PR body: 更新済み {pr_url}",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)
        # The offer must come before the reaction verification and summary.
        self.assertLess(
            content.index("### Offer a PR body update"),
            content.index("### Verify the final reaction state"),
        )

    def test_platform_adapters_define_pr_body_docs(self):
        adapters = {
            "ai/claude/skills/pr-comment-implement/SKILL.md": (
                "~/.claude/common/pr_body_core.md",
                "~/.claude/common/pr_body_format.md",
            ),
            "ai/gemini/commands/pr-comment-implement.toml": (
                "~/.gemini/common/pr_body_core.md",
                "~/.gemini/common/pr_body_format.md",
            ),
            "ai/codex/skills/pr-comment-implement/skill_head.md": (
                "~/.codex/skills/pr-body/SKILL.md",
            ),
        }
        for path, docs in adapters.items():
            text = (REPO_ROOT / path).read_text(encoding="utf-8")
            for doc in ("`<PR_BODY_DOCS>`", *docs):
                with self.subTest(path=path, doc=doc):
                    self.assertIn(doc, text)


if __name__ == "__main__":
    unittest.main()
