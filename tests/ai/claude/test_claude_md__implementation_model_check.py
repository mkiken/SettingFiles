import unittest

from support import REPO_ROOT


CLAUDE_MD_PATH = REPO_ROOT / "ai/claude/_CLAUDE.md"
HEADING = "# Implementation Model Check After Plan Approval"


class ImplementationModelCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = CLAUDE_MD_PATH.read_text(encoding="utf-8")
        cls.full = " ".join(text.split())
        start = text.index(HEADING)
        end = text.index("\n# ", start + len(HEADING))
        cls.section = " ".join(text[start:end].split())

    def test_section_heading_exists_and_old_fable_heading_is_gone(self):
        self.assertIn(HEADING, self.full)
        self.assertNotIn("Fable Model Check", self.full)

    def test_sonnet_and_haiku_skip_the_check(self):
        self.assertIn(
            "result starts with `claude-sonnet-` or `claude-haiku-`, proceed straight to implementation",
            self.section,
        )

    def test_stated_model_wins_over_the_stale_transcript(self):
        # opusplan 切替直後は transcript の最終 assistant が Opus のまま。通知の明記を優先する
        for required in (
            "A model named in a system prompt or notice",
            "wins over the transcript",
            "the stated model is Sonnet or Haiku",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.section)

    def test_other_models_get_a_recommended_delegation_choice(self):
        for required in (
            '`model: "haiku"`',
            '`model: "sonnet"`',
            "`(Recommended)`",
            "Continue with the current model.",
            "passing the full plan content in the prompt",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.section)

    def test_opus_and_manual_switch_stay_available_via_other(self):
        for required in ('`model: "opus"`', "manual model switch", "Delegated-Work Verification"):
            with self.subTest(required=required):
                self.assertIn(required, self.section)


if __name__ == "__main__":
    unittest.main()
