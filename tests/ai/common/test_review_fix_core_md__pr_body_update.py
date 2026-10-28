import unittest

from support import REPO_ROOT


CORE_PATH = REPO_ROOT / "ai/common/review_fix_core.md"


class ReviewFixPrBodyUpdateTest(unittest.TestCase):
    def test_finish_offers_full_pr_body_flow_only_after_a_push(self):
        content = " ".join(CORE_PATH.read_text(encoding="utf-8").split())
        for required in (
            "#### PR body update",
            "at least one group's `merge_action` is `commit_merge_push` and its push succeeded",
            "In Inline Flow, evaluate it only if the session's post-implementation workflow then pushes successfully.",
            "`PR bodyを更新する` / `更新しない`",
            "read <PR_BODY_DOCS> (adapter-defined)",
            "Confirmation Flow in full",
            "`--color=always` colored diff",
            "`### 変更点の概要`",
            "Never ask to apply a body from a summary alone.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)

    def test_offer_requires_an_accurate_existing_body_before_skipping(self):
        content = " ".join(CORE_PATH.read_text(encoding="utf-8").split())
        for required in (
            "already covers the pushed changes and remains accurate",
            "purpose, behavior, scope, and validation",
            "Test-only or other supporting changes can qualify",
            "never skip based on file type alone",
            "If even a test count or command becomes outdated, ask.",
            "If fetching the body or diff fails, or the assessment is uncertain, ask",
            "retry any failed context fetch before drafting",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)
        self.assertLess(content.index("Before asking, resolve"), content.index("Skip the offer"))
        self.assertLess(content.index("Skip the offer"), content.index("Otherwise ask once"))

    def test_platform_adapters_define_pr_body_docs(self):
        adapters = {
            "ai/claude/skills/review-fix/SKILL.md": (
                "~/.claude/common/pr_body_core.md",
                "~/.claude/common/pr_body_format.md",
            ),
            "ai/codex/skills/review-fix/skill_head.md": (
                "~/.codex/skills/pr-body/SKILL.md",
            ),
        }
        for path, docs in adapters.items():
            text = (REPO_ROOT / path).read_text(encoding="utf-8")
            for doc in ("<PR_BODY_DOCS>", "PR body update confirmation", *docs):
                with self.subTest(path=path, doc=doc):
                    self.assertIn(doc, text)


if __name__ == "__main__":
    unittest.main()
