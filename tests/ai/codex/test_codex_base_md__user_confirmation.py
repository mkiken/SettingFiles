import unittest

from support import REPO_ROOT


class UserConfirmationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (REPO_ROOT / "ai/codex/codex_base.md").read_text(
            encoding="utf-8"
        )
        cls.confirmation = cls.content.split("# User Confirmation\n", 1)[1].split(
            "\n# ", 1
        )[0]

    def test_optional_choice_ui_preserves_skill_options(self):
        self.assertIn("When using `request_user_input`", self.confirmation)
        self.assertIn("pass each label exactly once", self.confirmation)
        self.assertIn("preserve the authored option count", self.confirmation)
        self.assertIn("Do not count the client's auto-provided free-form `Other`", self.confirmation)

    def test_confirmation_does_not_force_a_method_over_runtime_rules(self):
        # Default mode prohibits permission requests through this tool and
        # numbered plain-text fallbacks; an empty optional answer may continue.
        for removed in (
            "use it for confirmation, clarification, cleanup, commit",
            "treat the UI as unavailable for that question",
            "Ask in plain text only when",
            "For a plain-text fallback with choices",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, self.content)

    def test_model_handoff_remains_a_separate_entrypoint(self):
        self.assertIn("# Plan Model Handoff\n", self.content)
        self.assertIn("load the `plan-model-handoff` skill", self.content)


if __name__ == "__main__":
    unittest.main()
