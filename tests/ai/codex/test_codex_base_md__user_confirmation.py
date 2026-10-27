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

    def test_confirmation_prefers_permitted_async_ui(self):
        self.assertIn("Prefer `request_user_input_async` for confirmations", self.confirmation)
        self.assertIn("when available and permitted for approval requests", self.confirmation)
        self.assertIn("Use `request_user_input` only for purposes permitted by the active runtime", self.confirmation)

    def test_choice_ui_preserves_skill_options(self):
        self.assertIn("For either UI", self.confirmation)
        self.assertIn("pass each skill-authored label exactly once", self.confirmation)
        self.assertIn("preserve the authored option count", self.confirmation)
        self.assertIn("Do not count the client's auto-provided free-form `Other`", self.confirmation)

    def test_confirmation_does_not_force_a_method_over_runtime_rules(self):
        # Runtime permission restrictions still govern request_user_input;
        # numbered fallbacks remain available for approvals.
        self.assertIn("never override its permission restrictions", self.confirmation)
        for removed in (
            "use it for confirmation, clarification, cleanup, commit",
            "treat the UI as unavailable for that question",
            "Ask in plain text only when",
            "For a plain-text fallback with choices",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, self.content)

    def test_confirmation_fallback_preserves_explicit_approval(self):
        self.assertIn("If no permitted UI is available or the authored options exceed its capacity", self.confirmation)
        self.assertIn("use a numbered plain-text list and accept number-only replies", self.confirmation)
        self.assertIn("Never treat an unanswered approval request as approval", self.confirmation)

    def test_model_handoff_remains_a_separate_entrypoint(self):
        self.assertIn("# Plan Model Handoff\n", self.content)
        self.assertIn("load the `plan-model-handoff` skill", self.content)


if __name__ == "__main__":
    unittest.main()
