import re
import unittest

from support import REPO_ROOT

SKILL = REPO_ROOT / "ai/common/shared_skills/pr-self-review-subagents"


class SelfReviewSubagentsContractTest(unittest.TestCase):
    def test_shared_deployment(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/pr-self-review-subagents"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), SKILL.resolve())
        self.assertFalse((REPO_ROOT / "ai/gemini/skills/pr-self-review-subagents").exists())

    def test_frontmatter_is_name_and_description_only(self):
        frontmatter = (SKILL / "SKILL.md").read_text().split("---", 2)[1]
        keys = re.findall(r"(?m)^([a-z-]+):", frontmatter)
        self.assertEqual(keys, ["name", "description"])

    def test_reuses_self_review_and_subagent_review(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        for contract in (
            "../pr-self-review/SKILL.md", "Establish the target", "Repair findings",
            "Hand off to the existing review workflow", "pr-review-subagents",
            "Result File", "/pr-comment-post", "read-only",
        ):
            self.assertIn(contract, text)

    def test_base_skill_is_untouched_one_reviewer_contract(self):
        base = (REPO_ROOT / "ai/common/shared_skills/pr-self-review/SKILL.md").read_text()
        self.assertIn("do not launch specialist or verifier agents", base)


if __name__ == "__main__":
    unittest.main()
