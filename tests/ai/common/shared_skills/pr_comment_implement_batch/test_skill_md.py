import re
import unittest

from support import REPO_ROOT

SKILL = REPO_ROOT / "ai/common/shared_skills/pr-comment-implement-batch"
ANALYSIS = REPO_ROOT / "ai/common/pr_comment_implement/analysis-design.md"
FINALIZATION = REPO_ROOT / "ai/common/pr_comment_implement/finalization.md"


class PrCommentImplementBatchContractTest(unittest.TestCase):
    def test_shared_deployment(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/pr-comment-implement-batch"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), SKILL.resolve())
        self.assertFalse((REPO_ROOT / "ai/gemini/skills/pr-comment-implement-batch").exists())

    def test_frontmatter_is_name_and_description_only(self):
        frontmatter = (SKILL / "SKILL.md").read_text().split("---", 2)[1]
        keys = re.findall(r"(?m)^([a-z-]+):", frontmatter)
        self.assertEqual(keys, ["name", "description"])

    def test_workflow_contracts(self):
        text = (SKILL / "SKILL.md").read_text()
        for contract in (
            "isResolved", "reviewThreads", "Skip selection", "/replies",
            "resolveReviewThread", "bot/self threads whose reply succeeded",
            "Inline", "read-only subagent", "Never force-push",
            "analysis-design.md", "Offer a PR body update",
        ):
            self.assertIn(contract, text)

    def test_review_bodies_and_issue_comments_are_handled(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        for contract in (
            "reviews(first:100)", "removing HTML comments",
            "issues/{n}/comments --paginate", "Keep only ROLE `other`",
            "already-replied-by-me", "contains the item's `html_url`",
            "[thread|review-body|issue-comment]",
            "standalone reply reference header", "pr_comment_implement/finalization.md",
            "not applicable",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)
        self.assertNotIn("out of scope", text)

    def test_bot_review_body_without_finding_is_dropped(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        for contract in (
            "carries no finding of its own", "Keep it when unsure",
            "除外: bot通知本文",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)

    def test_referenced_sections_still_exist(self):
        self.assertIn("Decide whether the comment should be acted on", ANALYSIS.read_text())
        finalization = FINALIZATION.read_text()
        self.assertIn("Offer a PR body update", finalization)
        self.assertIn("> 返信対象: [{one-line paraphrase}]({REPLY_REF_URL})", finalization)
        self.assertIn("`REPLY_PATH=standalone`", finalization)


if __name__ == "__main__":
    unittest.main()
