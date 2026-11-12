import unittest

from support import REPO_ROOT


SKILL = REPO_ROOT / "ai/common/shared_skills/review-consider"


class ReviewConsiderContractTest(unittest.TestCase):
    def test_platforms_share_the_orchestrator(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/review-consider"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), SKILL.resolve())

    def test_parallel_research_has_a_separate_role(self):
        role = SKILL / "references/considerer.md"
        self.assertTrue(role.is_file(), "Research needs a bounded role separate from orchestration")
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("considerer.md", text)
        self.assertNotIn("Do not use subagents.", text)
        role_text = role.read_text().lower()
        for required in ("item", "head", "test", "policy"):
            self.assertTrue(required in role_text, required)

    def test_rolling_flow_uses_existing_worktree_lifecycle(self):
        text = (SKILL / "SKILL.md").read_text().lower()
        for required in ("rolling", "approved", "worktree-task", "review-fix", "review-post"):
            self.assertTrue(required in text, required)
        self.assertNotIn("must reopen the report", text)

    def test_incremental_fix_contract_and_final_push(self):
        text = (REPO_ROOT / "ai/common/review_fix_core.md").read_text().lower()
        self.assertTrue("incremental considered fixes" in text, "Missing incremental fix entry")
        for required in ("append", "overlap", "resume", "push"):
            self.assertTrue(required in text, required)

    def test_final_action_survives_into_carryover(self):
        skill = (SKILL / "SKILL.md").read_text()
        merge = (REPO_ROOT / "ai/common/review_merge_core.md").read_text()
        for text in (skill, merge):
            self.assertTrue("action" in text, "Missing final action contract")
            self.assertIn("consider_state.json", text)
            self.assertIn("approved", text)


    def test_snapshot_and_approval_boundaries_are_explicit(self):
        text = (SKILL / "SKILL.md").read_text()
        for rule in (
            "immutable snapshot", "expected parent OID", "returns the item to `draft`",
            "Only one user confirmation", "one final posting pass",
            "a final push ends this snapshot", "Never write `state.json` or `merged.json`",
        ):
            self.assertTrue(rule in text, rule)

    def test_overlap_and_resume_preserve_unmerged_work(self):
        text = (REPO_ROOT / "ai/common/review_fix_core.md").read_text()
        for rule in (
            "A commit-only predecessor remains an overlap blocker",
            "without resetting other groups", "never re-baseline an unexplained change",
            "never offer or execute per-group push",
            "Resume skips recorded completed outcomes",
        ):
            self.assertTrue(rule in text, rule)

    def test_carryover_validates_the_previous_snapshot(self):
        text = (REPO_ROOT / "ai/common/review_merge_core.md").read_text()
        for rule in (
            "not the new/current PR head", "legacy action-less results yield null",
            "Explicit browser fix/post/dismiss decisions retain precedence",
        ):
            self.assertTrue(rule in text, rule)


    def test_generated_fix_and_report_documentation_match(self):
        core = (REPO_ROOT / "ai/common/review_fix_core.md").read_text()
        generated = (REPO_ROOT / "ai/codex/skills/review-fix/SKILL.md").read_text()
        self.assertTrue(core in generated, "Generated skill must contain current incremental flow")
        doc = (REPO_ROOT / ".claude/skills/ai-prompt-generation/references/report-servers.md").read_text()
        self.assertTrue("review-consider" in doc and "action" in doc)


if __name__ == "__main__":
    unittest.main()
