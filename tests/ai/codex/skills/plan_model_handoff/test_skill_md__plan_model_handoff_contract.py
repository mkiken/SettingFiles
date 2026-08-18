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

    def test_implementation_only_timing_keeps_new_plans_marker_free(self):
        for required in (
            "only immediately before the first implementation side effect",
            "Do not write an implementation-model marker into a newly finalized plan.",
            "completed `<proposed_plan>` before choosing how implementation runs",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

        # Exclusions ensure model selection follows plan review instead of
        # interrupting Plan Mode before the complete plan is visible.
        for excluded in (
            "Immediately before emitting the final `<proposed_plan>` in Plan Mode.",
            "At the Plan Mode checkpoint",
            "Implementation model: parent/<detected-sol-model-id>",
            "Implementation model: worker/<selected-runtime-model-id>",
        ):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, self.skill)

    def test_legacy_markers_remain_authoritative(self):
        for required in (
            "For backward compatibility",
            "Implementation model: parent/<model-id>",
            "Implementation model: worker/<model-id>",
            "Do not detect or ask again when a valid legacy marker exists.",
            "For a `parent/` marker, continue in the parent session.",
            "For a `worker/` marker, use exactly one `worker` subagent",
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
            "For an accepted plan without a valid legacy marker",
            "Implementation-model check skipped: active model detection failed.",
            "continue without asking",
            "continue silently without asking",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

    def test_manual_parent_model_switch_waits_without_side_effects(self):
        for required in (
            "Free-form `Other` means a manual parent-session model switch",
            "not Terra/Luna worker delegation",
            "Make no implementation change.",
            "wait until the user confirms the switch",
            "rerun detection on the next implementation attempt.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)


if __name__ == "__main__":
    unittest.main()
