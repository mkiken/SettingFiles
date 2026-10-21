import re
import unittest

from support import REPO_ROOT


PR_REVIEW_CORE = REPO_ROOT / "ai/common/pr_review_core.md"
ORCHESTRATOR_CORE = REPO_ROOT / "ai/common/pr_review_subagents/orchestrator_core.md"


def perspectives_section(text: str) -> str:
    return text.split("### Code Quality Perspectives", 1)[1].split("\n### ", 1)[0]


class PrReviewPerspectivesTest(unittest.TestCase):
    def setUp(self):
        self.core = PR_REVIEW_CORE.read_text(encoding="utf-8")

    def test_labels_match_subagent_dimensions(self):
        # pr-review and pr-review-subagents must review along the same 領域 so that
        # review / review-subagents results stay comparable.
        labels = re.findall(r"^- \*\*(\S+?)\*\*:", perspectives_section(self.core), flags=re.MULTILINE)
        label_line = next(
            line
            for line in ORCHESTRATOR_CORE.read_text(encoding="utf-8").splitlines()
            if line.startswith("Finding-header 領域 labels:")
        )
        expected = [label.strip(" .") for label in label_line.split(":", 1)[1].split(",")]
        self.assertEqual(sorted(labels), sorted(expected))

    def test_defect_assuming_stance_keeps_reporting_bar(self):
        section = perspectives_section(self.core)
        self.assertIn("Assume the change is broken somewhere", section)
        self.assertIn("if you cannot break it, report no finding", section)
        self.assertIn("never invent findings", section)


if __name__ == "__main__":
    unittest.main()
