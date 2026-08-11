import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"
AGENTS_PATH = REPO_ROOT / "ai/codex/_AGENTS.md"


class PlanReviewCriteriaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = CODEX_BASE_PATH.read_text(encoding="utf-8")
        cls.agents = AGENTS_PATH.read_text(encoding="utf-8")

    def test_skip_criterion_governs_both_offers(self):
        for required in (
            "governs both the `dig` skill offer and the Plan Review Presentation browser offer",
            "the shared file's own line-count/format criteria do not apply here",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_mechanical_plans_skip_both_offers(self):
        for required in (
            "renames, bulk replacements, reverts, single-file fixes with no design decision",
            "plans whose every task is a stated verbatim edit",
            "skip both",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_codex_has_no_plan_file_and_uses_an_ephemeral_browser_path(self):
        for required in (
            "Codex has no `~/.codex/plans` directory",
            "Do not reuse the fixed port 8600 / `~/.claude/plans` mount",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)
        # ~/.codex/plans does not exist; referencing it as a real target would
        # regress toward the Claude-only plan-file persistence model.
        self.assertNotIn("mounting `~/.codex/plans`", self.codex_base)

    def test_generated_agents_md_carries_the_same_criteria(self):
        for required in (
            "governs both the `dig` skill offer and the Plan Review Presentation browser offer",
            "Codex has no `~/.codex/plans` directory",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.agents)


if __name__ == "__main__":
    unittest.main()
