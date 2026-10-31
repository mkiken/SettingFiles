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

    def test_confirmation_prefers_sync_without_automatic_async_fallback(self):
        self.assertIn("Prefer `request_user_input`", self.confirmation)
        self.assertIn("do not automatically switch to `request_user_input_async`", self.confirmation)
        self.assertIn("Follow the active runtime's mode and purpose restrictions", self.confirmation)

    def test_choice_ui_preserves_skill_options(self):
        self.assertIn("Preserve every skill-authored choice's wording, order, and meaning", self.confirmation)
        self.assertIn("`request_user_input` `options[].label` or `request_user_input_async` `options[]`", self.confirmation)
        self.assertIn("omit only a leading enumeration prefix such as `1. ` or `1) `", self.confirmation)
        self.assertIn("preserve numbers in the choice text, including `2FA`", self.confirmation)
        self.assertIn("Do not add a custom free-input choice or count or rename `Other` as an authored choice", self.confirmation)

    def test_choice_ui_omits_prefix_but_plain_text_keeps_enumeration(self):
        self.assertIn("Keep enumeration numbers in question text, ordinary prose, and numbered plain-text choices", self.confirmation)
        self.assertIn("Always show the complete numbered list in an ordinary assistant message when asking a choice question", self.confirmation)
        self.assertIn("regardless of choice count or whether a choice UI is used", self.confirmation)
        self.assertIn("do not rely on UI rendering being confirmed", self.confirmation)
        self.assertIn("Include the same numbered list in the UI question text", self.confirmation)

    def test_large_choice_sets_use_other_without_losing_choices(self):
        self.assertIn("For four or more choices, expose only the first two choices", self.confirmation)
        self.assertIn("expose only the first two choices without enumeration prefixes in the UI options", self.confirmation)
        self.assertIn("enter any choice number in the client's auto-provided free-form `Other`", self.confirmation)
        self.assertIn("Never omit a choice from the complete list or split the decision across questions", self.confirmation)

    def test_number_only_reply_selects_the_displayed_choice(self):
        self.assertIn("Interpret a number-only reply, including text entered in `Other`, against the complete authored list", self.confirmation)
        self.assertIn("The UI position of `Other` does not select authored choice 3", self.confirmation)
        self.assertIn("Empty, out-of-range, multiple-number, or ambiguous answers require clarification before action", self.confirmation)
        self.assertIn("preserve explicit free-form routes defined by the skill", self.confirmation)

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
        self.assertIn("If `request_user_input` is unavailable or not permitted for the purpose", self.confirmation)
        self.assertIn("use a numbered plain-text list and accept number-only replies", self.confirmation)
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
