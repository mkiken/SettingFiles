import unittest

from support import REPO_ROOT


SKILL_PATH = REPO_ROOT / "ai/codex/skills/dig/SKILL.md"


class DigSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_frontmatter_uses_the_cross_platform_subset(self):
        frontmatter = self.skill.split("---", 2)[1]
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: dig", frontmatter)

    def test_uses_request_user_input_with_a_numbered_fallback(self):
        for required in (
            "request_user_input",
            "Markdown ordered list starting from `1.`",
            "number-only reply selects that option",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_does_not_regress_to_claude_only_primitives(self):
        # Codex has no AskUserQuestion, TodoWrite, allowed-tools frontmatter, or
        # context:fork subagent forking — copying the Claude dig command verbatim
        # would silently fail on this runtime, so these must never reappear here.
        for forbidden in ("AskUserQuestion", "TodoWrite", "allowed-tools", "context: fork"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.skill)

    def test_loops_across_rounds_with_a_bounded_exit(self):
        for required in (
            "return to Phase 3",
            "Do not loop indefinitely",
            "two consecutive dry rounds",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_covers_all_six_assumption_categories(self):
        for category in (
            "Feasibility",
            "User",
            "Scope",
            "Dependency",
            "Timeline",
            "Architectural",
        ):
            with self.subTest(category=category):
                self.assertIn(f"**{category}**", self.skill)

    def test_persists_decisions_by_rewriting_the_response_not_a_file(self):
        for required in (
            "there is no plan file to write back to",
            "Codex has no `~/.codex/plans`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_goes_at_least_two_levels_deep_before_switching_topics(self):
        for required in (
            "at least 2 levels deep",
            "Depth over breadth",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)


if __name__ == "__main__":
    unittest.main()
