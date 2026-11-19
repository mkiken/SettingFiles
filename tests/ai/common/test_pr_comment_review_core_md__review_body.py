import unittest

from support import REPO_ROOT


CORE = REPO_ROOT / "ai/common/pr_comment_review_core.md"


class PrCommentReviewCoreReviewBodyTest(unittest.TestCase):
    def test_review_body_is_analyzed_with_inline_comments(self):
        content = CORE.read_text(encoding="utf-8")
        bullet = content.split("- Pull Request Review:", 1)[1].split("- Issue Comment:", 1)[0]
        normalized = " ".join(bullet.split())
        for requirement in (
            "`.../reviews/{review_id}` body fetch",
            "non-empty after removing HTML comments",
            "analyze it together with the inline comments",
            "full thread",
            "the summary if none",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, normalized)


if __name__ == "__main__":
    unittest.main()
