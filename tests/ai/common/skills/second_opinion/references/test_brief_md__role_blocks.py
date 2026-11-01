import unittest

from support import REPO_ROOT


BRIEF = REPO_ROOT / "ai/common/skills/second-opinion/references/brief.md"


class SecondOpinionBriefTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = BRIEF.read_text(encoding="utf-8")

    def test_every_role_mode_has_a_block(self):
        for heading in ("### `--review`", "### `--debug`", "### `--plan`"):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.text)

    def test_template_forbids_delegation_and_requires_grounding(self):
        for required in (
            "<no_delegation>",
            "Do not call or consult any other AI or agent.",
            "<grounding_rules>",
            "Do not invent files, lines, behavior, or incidents.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.text)

    def test_independent_mode_carries_no_caller_answer(self):
        self.assertIn("Independent (default): no `caller_answer` block.", self.text)
        self.assertIn("<caller_answer>", self.text)

    def test_question_facts_and_unverified_are_separate_blocks(self):
        for required in ("<task>", "<known_facts>", "<unverified>"):
            with self.subTest(required=required):
                self.assertIn(required, self.text)
        self.assertIn("no conclusions, hypotheses, or proposed solutions", self.text)
        self.assertIn("Facts and unverified points are still passed.", self.text)

    def test_contract_has_context_request_and_completion_marker(self):
        for required in ("## Context request", "__END_OF_ANSWER__", "<follow_up>"):
            with self.subTest(required=required):
                self.assertIn(required, self.text)

    def test_no_write_capable_flags(self):
        for flag in ("--write", "workspace-write", "auto_edit", "acceptEdits"):
            with self.subTest(flag=flag):
                self.assertNotIn(flag, self.text)

    def test_review_block_keeps_the_finding_bar(self):
        for required in ("<operating_stance>", "<attack_surface>", "<finding_bar>", "needs-attention or approve"):
            with self.subTest(required=required):
                self.assertIn(required, self.text)


if __name__ == "__main__":
    unittest.main()
