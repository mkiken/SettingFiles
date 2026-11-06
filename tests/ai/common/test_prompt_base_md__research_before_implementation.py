import unittest

from support import REPO_ROOT


class ResearchBeforeImplementationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(encoding="utf-8")
        cls.section = content.split("## Research Before Implementation\n", 1)[1].split(
            "\n## Simplicity First", 1
        )[0]

    def test_unfamiliar_work_starts_with_existing_code_and_official_docs(self):
        self.assertIn(
            "For unfamiliar features, protocols, or integrations, consult existing code "
            "and official documentation first.",
            self.section,
        )

    def test_oss_comparison_resolves_uncertainty_before_selecting_smallest_fit(self):
        self.assertIn(
            "Where design uncertainty remains, compare mature GitHub implementations, "
            "tests, and relevant issues; explain their applicable conditions, "
            "dependencies, and differences from the current requirements before "
            "choosing the smallest suitable implementation.",
            self.section,
        )

    def test_simple_changes_do_not_require_unrelated_research_or_dependencies(self):
        self.assertIn(
            "Simple changes do not require unrelated research or additional dependencies.",
            self.section,
        )


if __name__ == "__main__":
    unittest.main()
