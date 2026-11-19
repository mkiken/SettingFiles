import unittest

from support import REPO_ROOT

FORMAT = REPO_ROOT / "ai/common/pr_body_format.md"
REFERENCING = (
    REPO_ROOT / "ai/common/pr_create_by_branch_core.md",
    REPO_ROOT / "ai/common/pr_body_core.md",
    REPO_ROOT / "ai/codex/skills/pr-create-by-branch/SKILL.md",
    REPO_ROOT / "ai/codex/skills/pr-body/SKILL.md",
)

HEADING = "### Review Focus Points"
REFERENCE = "Review Focus Points section"


def rule_section():
    content = FORMAT.read_text(encoding="utf-8")
    start = content.index(HEADING)
    end = content.find("\n### ", start + 1)
    end = len(content) if end == -1 else end
    return content[start:end]


class ReviewFocusPointsRuleTest(unittest.TestCase):
    def test_only_user_decisions_become_candidates(self):
        section = rule_section()
        self.assertIn("design decisions the user made in this conversation", section)
        self.assertIn("Never write conclusions the AI reached alone", section)

    def test_confirmation_offers_the_three_choices(self):
        section = rule_section()
        for choice in ("`記載する`", "`修正する`", "`記載しない`"):
            self.assertIn(choice, section)

    def test_no_candidates_defaults_without_asking(self):
        section = rule_section()
        self.assertIn("`特になし`) without asking", section)

    def test_existing_content_is_not_overwritten(self):
        self.assertIn("Never overwrite existing non-default content", rule_section())

    def test_pr_paths_reference_rule(self):
        for path in REFERENCING:
            self.assertIn(REFERENCE, path.read_text(encoding="utf-8"), path.name)


if __name__ == "__main__":
    unittest.main()
