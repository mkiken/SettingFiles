import unittest

from support import REPO_ROOT


PR_REVIEW_CORE = REPO_ROOT / "ai/common/pr_review_core.md"


class PrReviewCoreResultFileOutputTest(unittest.TestCase):
    def setUp(self):
        self.core = PR_REVIEW_CORE.read_text(encoding="utf-8")

    def test_configured_output_path_is_pre_authorized(self):
        self.assertIn(
            "A non-empty value is explicit, workflow-provided authorization",
            self.core,
        )
        self.assertIn(
            "Do not ask for confirmation, including when the path is outside "
            "the session project.",
            self.core,
        )

    def test_unset_output_path_skips_write(self):
        self.assertIn(
            "If the variable is unset or empty, skip this section entirely.",
            self.core,
        )

    def test_saved_markdown_matches_final_output_even_without_findings(self):
        self.assertIn("write the exact same markdown", self.core)
        self.assertIn("対応が必要な指摘はありません。", self.core)


if __name__ == "__main__":
    unittest.main()
