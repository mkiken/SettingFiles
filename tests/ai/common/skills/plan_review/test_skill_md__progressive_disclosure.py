import unittest

from support import REPO_ROOT


SKILL_DIR = REPO_ROOT / "ai/common/skills/plan-review"
SKILL_PATH = SKILL_DIR / "SKILL.md"
PROMPT_PATH = REPO_ROOT / "ai/common/prompt_base.md"


class PlanReviewProgressiveDisclosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = " ".join(SKILL_PATH.read_text(encoding="utf-8").split())
        cls.prompt = " ".join(PROMPT_PATH.read_text(encoding="utf-8").split())

    def test_shared_prompt_routes_only_eligible_plans(self):
        for condition in (
            "SDD spec/design/tasks document",
            "100 lines or longer",
            "contains mermaid diagrams, tables, or images",
            "spans multiple files",
        ):
            with self.subTest(condition=condition):
                self.assertIn(condition, self.prompt)
        self.assertIn("load the `plan-review` skill", self.prompt)
        self.assertNotIn("mdv -d -n -q", self.prompt)

    def test_entrypoint_routes_to_one_platform_reference(self):
        references = {
            "Codex": "references/codex.md",
            "Claude": "references/claude.md",
            "Gemini": "references/gemini.md",
        }
        for platform, reference in references.items():
            with self.subTest(platform=platform):
                self.assertIn(f"{platform}: `{reference}`", self.skill)
                self.assertTrue((SKILL_DIR / reference).is_file())
        self.assertIn("Read exactly one platform workflow", self.skill)

    def test_browser_mechanics_load_only_after_browser_selection(self):
        browser = SKILL_DIR / "references/browser.md"
        self.assertTrue(browser.is_file())
        self.assertIn("only when the user chooses browser review", self.skill)
        self.assertNotIn("mdv -d -n -q", self.skill)
        self.assertIn("mdv -d -n -q", browser.read_text(encoding="utf-8"))

    def test_missing_reference_stops_before_external_effects(self):
        self.assertIn("missing or unreadable", self.skill)
        self.assertIn("stop before opening a browser", self.skill)


if __name__ == "__main__":
    unittest.main()
