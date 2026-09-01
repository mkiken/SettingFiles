import unittest

from support import REPO_ROOT


HEAD_PATH = REPO_ROOT / "ai/codex/skills/config-audit/skill_head.md"
CORE_PATH = REPO_ROOT / "ai/common/config_audit_subagents/orchestrator_core.md"
CLAUDE_PATH = REPO_ROOT / "ai/claude/skills/config-audit/SKILL.md"
GEMINI_PATH = REPO_ROOT / "ai/gemini/commands/config-audit.toml"


class CodexConfigAuditDispatchContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.head = HEAD_PATH.read_text(encoding="utf-8")
        cls.core = CORE_PATH.read_text(encoding="utf-8")

    def test_codex_dispatches_by_available_slot_waves(self):
        self.assertIn("waves sized to the child-agent slots available at runtime", self.head)
        self.assertNotIn("spawn all six in parallel", self.head)
        self.assertIn("Do not hard-code a slot count", self.head)

    def test_capacity_failure_retries_the_same_specialist(self):
        self.assertIn("capacity error as temporary", self.head)
        self.assertIn("retry the same specialist", self.head)

    def test_role_fallback_is_confirmed_and_scoped(self):
        for token in ("stop safely (recommended)", "default agent", "config_auditor_<dimension>.toml", "fork_turns=none"):
            with self.subTest(token=token):
                self.assertIn(token, self.head)
        self.assertIn("prohibit writes and subagents", self.head)

    def test_invalid_or_missing_dimension_stops_before_report(self):
        self.assertIn("stop without generating a partial audit or report", self.head)
        self.assertIn("Do not enter Phase 3 until every dimension has one valid result", self.core)

    def test_shared_core_defers_schedule_to_the_adapter(self):
        self.assertIn("platform adapter's dispatch schedule", self.core)
        self.assertIn("start all six simultaneously", CLAUDE_PATH.read_text(encoding="utf-8"))
        self.assertIn("wait_for_previous=false", GEMINI_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
