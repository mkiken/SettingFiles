import unittest

from support import REPO_ROOT


SKILL_PATH = REPO_ROOT / "ai/claude/skills/grilling/SKILL.md"


class GrillingSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_frontmatter_uses_the_cross_platform_subset(self):
        frontmatter = self.skill.split("---", 2)[1]
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: grilling", frontmatter)

    def test_frontier_ordering_is_the_defining_mechanism(self):
        # This dependency ordering is what distinguishes grilling from dig,
        # which ranks questions by risk instead. Losing it collapses the two
        # skills into the same thing and removes the reason to run both.
        for required in (
            "prerequisites are already settled",
            "belongs to a *later* round, not this one",
            "Ask the whole frontier in one round",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_every_question_carries_a_recommended_answer(self):
        for required in (
            "Every question carries your recommended answer",
            "(推奨)",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_facts_are_looked_up_and_decisions_go_to_the_user(self):
        for required in (
            "Finding **facts** is your job, never the user's",
            "Never ask the user for anything you could look up yourself",
            "The **decisions** are the user's",
            "Do not block on it",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_interview_runs_inline_rather_than_forked(self):
        # A forked agent cannot reach the user with a question, so forking the
        # interview itself would silently void the entire skill.
        for required in (
            "Run inline in this session",
            "a subagent for the interview itself",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_terminates_on_an_empty_frontier_with_user_confirmation(self):
        for required in (
            "done when the frontier is empty",
            "Do not act on the plan until they confirm",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_records_decisions_with_their_dependencies(self):
        for required in (
            "## Decisions",
            "Depends on",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_credits_the_upstream_mit_source(self):
        for required in (
            "Matt Pocock",
            "MIT",
            "github.com/mattpocock/skills",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_uses_ask_user_question_not_plain_text(self):
        for required in (
            "Use `AskUserQuestion`",
            "misfires the Stop hook",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_splits_a_wide_frontier_across_calls_rather_than_dropping_questions(self):
        # AskUserQuestion caps at 4 questions per call. Without this rule the
        # model would silently drop frontier questions or merge distinct
        # decisions into one option list to fit the cap.
        for required in (
            "at most 4 questions per call",
            "split it across consecutive `AskUserQuestion` calls",
            "rather than dropping questions",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_persists_decisions_to_the_plan_file(self):
        for required in (
            "~/.claude/plans/",
            "a decision that lives only in chat is lost",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

if __name__ == "__main__":
    unittest.main()
