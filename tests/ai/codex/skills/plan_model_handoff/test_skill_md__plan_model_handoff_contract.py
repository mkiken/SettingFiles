import unittest

from support import REPO_ROOT


SKILL_PATH = REPO_ROOT / "ai/codex/skills/plan-model-handoff/SKILL.md"


class PlanModelHandoffSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_frontmatter_uses_the_cross_platform_subset(self):
        frontmatter = self.skill.split("---", 2)[1]
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: plan-model-handoff", frontmatter)

    def test_detects_the_latest_model_from_the_current_thread(self):
        for required in (
            "${CODEX_THREAD_ID:-}",
            '"$HOME/.codex/sessions"',
            '"*-${CODEX_THREAD_ID}.jsonl"',
            '.type == "turn_context"',
            '.type == "world_state"',
            ".payload.model // .payload.state.model // empty",
            "tail -1",
            'match `*-sol`',
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_plan_checkpoint_records_one_authoritative_marker(self):
        for required in (
            'final `<proposed_plan>`',
            "Do not detect or ask again when a valid marker exists.",
            "Implementation model: parent/<detected-sol-model-id>",
            "Implementation model: worker/<selected-runtime-model-id>",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_choice_flow_preserves_all_execution_routes(self):
        for required in (
            "`Continue with Sol (Recommended)`",
            "`Use Terra subagent`",
            "`Use Luna subagent`",
            "the parent session remains on Sol; exactly one Terra `worker` subagent performs implementation; the parent retains decisions, integration, and verification.",
            "the parent session remains on Sol; exactly one Luna `worker` subagent performs implementation; the parent retains decisions, integration, and verification.",
            "Resolve Terra and Luna only from callable runtime metadata",
            "If the selected tier is unavailable, make no implementation change",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

        # Excluding the old labels prevents readers from mistaking delegation for a parent-model switch.
        for excluded in ("`Delegate to Terra`", "`Delegate to Luna`"):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, self.skill)

    def test_implementation_fallback_and_detection_failure_are_non_blocking(self):
        for required in (
            "first implementation side effect for an accepted plan",
            "for a plan without a marker",
            "Implementation-model check skipped: active model detection failed.",
            "continue without asking",
            "continue silently without asking",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)


if __name__ == "__main__":
    unittest.main()
