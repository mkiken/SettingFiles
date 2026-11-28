import unittest

from support import REPO_ROOT


class ReviewMergeServerLifecycleTest(unittest.TestCase):
    """Herdr内ではレポートサーバーを前面タブで動かす（Ctrl-Cを明示終了に使うため）。

    手順は共通コアにあり、Claude（実行時に共通コアを読む）とCodex（生成SKILL.mdへ
    コアが埋め込まれる）の両方へ届く。
    """

    def test_core_defines_herdr_foreground_startup(self):
        core = (REPO_ROOT / "ai/common/review_merge_core.md").read_text()

        for requirement in (
            "HERDR_ENV=1",
            "/api/info",
            "resolved `<RUN_DIR>`",
            "no-focus Herdr tab",
            "--cwd <RUN_DIR>",
            "exec python3 ~/.config/ai-pr/bin/serve_review_report.py",
            "independently fetch the report URL in a later tool call",
            "close only the tab created for this attempt",
            "Outside Herdr, use the fallback below",
            "review-cleanup <RUN_DIR>",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, core)

    def test_codex_generated_skill_embeds_the_core_procedure(self):
        head = (REPO_ROOT / "ai/codex/skills/review-merge/skill_head.md").read_text()
        generated = (REPO_ROOT / "ai/codex/skills/review-merge/SKILL.md").read_text()
        core = (REPO_ROOT / "ai/common/review_merge_core.md").read_text()

        self.assertIn(head, generated)
        self.assertIn(core, generated)
        # 手順はコアへ一本化済み。Codex側headに古い重複手順を残さない
        self.assertNotIn("no-focus Herdr tab", head)

    def test_claude_adapter_may_run_herdr_and_reads_the_core(self):
        adapter = (REPO_ROOT / "ai/claude/skills/review-merge/SKILL.md").read_text()
        self.assertIn("Bash(herdr:*)", adapter)
        self.assertIn("review_merge_core.md", adapter)

    def test_generation_doc_records_herdr_startup(self):
        generation = (REPO_ROOT / ".claude/skills/ai-prompt-generation/references/generation.md").read_text()
        self.assertIn("starts the report server in a Herdr tab", generation)


if __name__ == "__main__":
    unittest.main()
