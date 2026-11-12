import unittest
from pathlib import Path

from support import REPO_ROOT

SKILL = REPO_ROOT / "ai/common/shared_skills/pr-self-review"


class SelfReviewContractTest(unittest.TestCase):
    def test_shared_deployment(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/pr-self-review"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), SKILL.resolve())
        # Only the approved Claude/Codex integrations support this editing flow.
        self.assertFalse((REPO_ROOT / "ai/gemini/skills/pr-self-review").exists())

    def test_approval_and_completion_boundaries(self):
        text = (SKILL / "SKILL.md").read_text()
        for contract in (
            "HEAD matching headRefOid", "including untracked files",
            "For EVERY behavior change", "BEFORE editing",
            "If behavior preservation is uncertain",
            "Never mark a failed or unverified repair complete",
            "changes remain uncommitted and unpushed",
        ):
            self.assertIn(contract, text)

    def test_existing_report_workflow_is_reused(self):
        text = (SKILL / "SKILL.md").read_text()
        for contract in (
            "pr_review_finding_format.md", "ai_review_run_dir.sh <PR_NUMBER>",
            "Invoke the existing `review-merge` skill",
            "review-consider, review-fix and review-post",
            "Write the no-findings", "Do not include",
        ):
            self.assertIn(contract, text)
        # State and HTML lifecycle stay owned by review-merge and its consumers.
        self.assertNotIn("schema_version:", text)
