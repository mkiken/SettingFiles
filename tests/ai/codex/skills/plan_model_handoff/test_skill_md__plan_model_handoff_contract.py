import unittest

from support import REPO_ROOT


SKILL_PATH = REPO_ROOT / "ai/codex/skills/plan-model-handoff/SKILL.md"


class PlanModelHandoffSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        cls.normalized_skill = " ".join(cls.skill.split())

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
            "is `gpt-6-astra`",
            'match `*-sol`',
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

    def test_execution_entry_timing_keeps_new_plans_marker_free(self):
        for required in (
            "when beginning execution of an accepted plan",
            "before starting any task-specific workflow or repository operation",
            "Do not write an implementation-model marker into a newly finalized plan.",
            "completed `<proposed_plan>` before choosing how implementation runs",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

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

    def test_legacy_plan_markers_are_removed(self):
        for excluded in (
            "Implementation model: parent/<model-id>",
            "Implementation model: worker/<model-id>",
            "valid legacy marker",
            "For backward compatibility",
        ):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, self.skill)

    def test_choice_flow_offers_sol_and_terra_delegation(self):
        for required in (
            "`Use Sol subagent (Recommended)`",
            "`Use Terra subagent`",
            "parent session remains on the detected model",
            "exactly one Sol `worker` subagent owns the entire accepted-plan execution.",
            "exactly one Terra `worker` subagent owns the entire accepted-plan execution.",
            "Resolve Sol, Terra, and Luna only from callable runtime metadata",
            "If the selected tier is unavailable, make no implementation change",
            "do not count the client's auto-provided free-form `Other` as an authored option",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

        # Excluding old labels keeps the authored choices limited to the two preferred worker tiers.
        for excluded in (
            "`Continue with Sol (Recommended)`",
            "`Delegate to Terra`",
            "`Delegate to Luna`",
            "`Continue with current model (Recommended)`",
            "`Use Luna subagent`",
        ):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, self.skill)

    def test_other_routes_model_names_without_assuming_a_parent_switch(self):
        for required in (
            'In the question text, say that `Other` can specify "continue with the current model", "delegate to Luna", or "switch the parent model manually".',
            "A supported model name without an explicit parent-switch request delegates to that model's `worker`",
            "including free-form answers such as `I want to use Sol`",
            "Do not interpret free-form `Other` as a manual parent-model switch by default.",
            "If the route is unclear, ask the user to clarify before making any implementation change.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

    def test_other_preserves_current_luna_and_explicit_parent_switch_routes(self):
        for required in (
            "A request to continue with the current model keeps execution in the parent session.",
            "A Luna request delegates the full lifecycle to exactly one Luna `worker` subagent.",
            "Only an explicit request to switch the parent-session model starts the manual-switch flow.",
            "Make no implementation change while waiting for that switch.",
            "wait until the user confirms the switch",
            "rerun detection on the next implementation attempt.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

    def test_worker_owns_the_full_execution_lifecycle(self):
        for required in (
            '`fork_turns="none"`',
            "The accepted plan verbatim, the original task request, and every accepted user decision.",
            "including an explicit `$worktree-task ...` entry when present",
            "task-workflow setup and state capture",
            "implementation, verification, user confirmations, commits, merges",
            "in-scope PR or issue replies and resolution",
            "independent side-effect verification, and the final report",
            "delegation grants no new authority",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

    def test_parent_only_relays_and_never_takes_over(self):
        for required in (
            "send the exact question and authored choices to the parent",
            "The parent relays them unchanged",
            "makes no decision on the worker's behalf",
            "must not independently inspect or change the repository",
            "run verification, integrate changes, commit, push",
            "must not retry, spawn a replacement, or continue with the detected parent model",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.normalized_skill)

    def test_implementation_fallback_and_detection_failure_are_non_blocking(self):
        for required in (
            "beginning execution of an accepted plan",
            "Apply the selected execution route to the current task",
            "Implementation-model check skipped: active model detection failed.",
            "continue without asking",
            "continue silently without asking",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.skill)

if __name__ == "__main__":
    unittest.main()
