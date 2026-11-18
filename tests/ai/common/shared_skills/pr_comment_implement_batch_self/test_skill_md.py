import re
import unittest

from support import REPO_ROOT

SKILL = REPO_ROOT / "ai/common/shared_skills/pr-comment-implement-batch-self"
BATCH = REPO_ROOT / "ai/common/shared_skills/pr-comment-implement-batch/SKILL.md"
SELF_REVIEW = REPO_ROOT / "ai/common/shared_skills/pr-self-review/SKILL.md"


class PrCommentImplementBatchSelfContractTest(unittest.TestCase):
    def test_shared_deployment(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/pr-comment-implement-batch-self"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), SKILL.resolve())
        self.assertFalse((REPO_ROOT / "ai/gemini/skills/pr-comment-implement-batch-self").exists())

    def test_frontmatter_is_name_and_description_only(self):
        frontmatter = (SKILL / "SKILL.md").read_text().split("---", 2)[1]
        keys = re.findall(r"(?m)^([a-z-]+):", frontmatter)
        self.assertEqual(keys, ["name", "description"])

    def test_workflow_contracts(self):
        text = (SKILL / "SKILL.md").read_text()
        for contract in (
            "../pr-comment-implement-batch/SKILL.md", "../pr-self-review/SKILL.md",
            "Repair findings", "`auto`", "`approval`", "not skip candidates",
            "demote it to `approval`", "commit that thread alone",
            "Never commit unverified work", "never force-push",
        ):
            self.assertIn(contract, text)

    def test_referenced_sections_still_exist(self):
        batch = BATCH.read_text()
        for section in ("Establish the target", "Collect threads", "Choose flow",
                        "Analyst brief", "Per-thread loop", "Finalize"):
            self.assertIn(f"## {section}", batch)
        self.assertIn("## Repair findings", SELF_REVIEW.read_text())


if __name__ == "__main__":
    unittest.main()
