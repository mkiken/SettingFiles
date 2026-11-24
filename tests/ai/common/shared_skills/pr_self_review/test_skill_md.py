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
            "## Confirm commit and push", "Post-Implementation Workflow",
            "Never skip it as \"review-only work\"",
            "without the user's choice",
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

    def test_multi_ai_run_mode_contract(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        for contract in (
            "--from-run <RUN_DIR>", "<RUN_DIR>/self_fix",
            "only completed repairs leave the remaining set",
            "Leave the original RUN_DIR unchanged",
        ):
            self.assertIn(contract, text)

    def test_resuming_after_head_update_requires_verified_fast_forward(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        for contract in (
            "belongs to the current repository and PR", "refs/pull/<PR_NUMBER>/head",
            "FETCH_HEAD", "git merge --ff-only", "local HEAD is an ancestor",
            "re-check that the branch, local HEAD and clean status",
        ):
            self.assertIn(contract, text)

    def test_updated_head_findings_are_reverified_and_reanchored(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        for contract in (
            "If the SHA matches", "If the SHA differs",
            "re-verify every imported finding", "report resolved findings with evidence",
            "report unverifiable findings in the conversation",
            "map each remaining finding to the verified path and lines",
        ):
            self.assertIn(contract, text)
