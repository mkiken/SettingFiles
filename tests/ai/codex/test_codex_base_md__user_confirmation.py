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

    def test_confirmation_requires_a_usable_choice_ui(self):
        self.assertIn("For every required user confirmation or decision", self.confirmation)
        self.assertIn("use a choice UI whenever a callable, permitted tool can present all options in one question", self.confirmation)
        self.assertIn("Do not replace a usable choice UI with a prose question", self.confirmation)
        self.assertIn("do not reconfirm already-authorized work", self.confirmation)

    def test_confirmation_selects_sync_then_async_when_supported(self):
        self.assertIn("Choose `request_user_input` first if it supports the purpose and all options", self.confirmation)
        self.assertIn("otherwise use `request_user_input_async` if it does", self.confirmation)
        self.assertIn("Follow the active runtime's mode and purpose restrictions", self.confirmation)

    def test_choice_ui_preserves_skill_options(self):
        self.assertIn("For either UI", self.confirmation)
        self.assertIn("pass each skill-authored label exactly once", self.confirmation)
        self.assertIn("preserve its wording, order, and authored option count", self.confirmation)
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
        self.assertIn("If no permitted UI can present every option in one question", self.confirmation)
        self.assertIn("use a numbered plain-text list and accept number-only replies", self.confirmation)
        self.assertIn("Never split a choice set into multiple questions or omit/group options to fit a UI", self.confirmation)
        self.assertIn("Never treat an unanswered approval request as approval", self.confirmation)

    def test_async_acknowledgements_and_empty_answers_do_not_authorize_work(self):
        self.assertIn("An async acknowledgement only means the question was accepted", self.confirmation)
        self.assertIn("wait for the user's answer before dependent work", self.confirmation)
        self.assertIn("Do not duplicate a pending question", self.confirmation)
        self.assertIn("Empty responses and missing selections are not approval", self.confirmation)

    def test_inherently_free_form_answers_do_not_get_artificial_choices(self):
        self.assertIn("When the answer inherently needs free-form input", self.confirmation)
        self.assertIn("keep it free-form; do not invent choices", self.confirmation)

    def test_skill_sources_delegate_confirmation_presentation_to_the_base(self):
        paths = (
            "ai/codex/skills/review-fix/skill_head.md",
            "ai/codex/skills/audit-fix/skill_head.md",
            "ai/codex/skills/config-audit/skill_head.md",
            "ai/codex/skills/pr-create-by-branch/skill_head.md",
            "ai/codex/skills/plan-model-handoff/SKILL.md",
            "ai/codex/skills/grilling/SKILL.md",
            "ai/codex/skills/dig/SKILL.md",
            "ai/common/skills/plan-review/references/codex.md",
        )
        for path in paths:
            with self.subTest(path=path):
                content = " ".join((REPO_ROOT / path).read_text(encoding="utf-8").split())
                self.assertIn("always-on `# User Confirmation` rules", content)

    def test_model_handoff_remains_a_separate_entrypoint(self):
        self.assertIn("# Plan Model Handoff\n", self.content)
        self.assertIn("load the `plan-model-handoff` skill", self.content)


if __name__ == "__main__":
    unittest.main()
