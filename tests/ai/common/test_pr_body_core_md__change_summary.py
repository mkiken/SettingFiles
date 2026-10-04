import unittest

from support import REPO_ROOT

CORE = REPO_ROOT / "ai/common/pr_body_core.md"
CODEX_PR_BODY = REPO_ROOT / "ai/codex/skills/pr-body/SKILL.md"

SUMMARY_HEADER = "### 変更点の概要"


class PrBodyCoreChangeSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

    def test_summary_follows_diff_and_precedes_confirmation(self):
        # 生diffだけでは変更内容を把握しにくいため、diff表示の後・確認質問の前に概要を出す。
        diff_header = self.content.index("### 既存body → 新bodyの変更差分")
        summary = self.content.index(SUMMARY_HEADER)
        confirm = self.content.index("このPR bodyをPR #<PR_NUMBER> に反映しますか？")
        self.assertLess(diff_header, summary)
        self.assertLess(summary, confirm)

    def test_summary_covers_every_hunk_without_omission(self):
        self.assertIn("Every hunk must map to at least one bullet", self.content)
        self.assertIn("omit nothing", self.content)
        self.assertIn("Derive it from the pasted `--no-color` diff", self.content)

    def test_summary_skipped_for_empty_existing_body(self):
        self.assertIn("skip the change summary below", self.content)

    def test_codex_generated_skill_includes_summary(self):
        self.assertIn(SUMMARY_HEADER, CODEX_PR_BODY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
