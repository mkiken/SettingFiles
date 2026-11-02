import unittest
from pathlib import Path

from support import REPO_ROOT


class SyncSettingsContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = REPO_ROOT / ".claude/skills/sync-settings/SKILL.md"
        cls.content = cls.skill.read_text(encoding="utf-8")

    def assert_contract(self, *phrases):
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.content)

    def test_local_codex_link_resolves_to_claude_source(self):
        link = REPO_ROOT / ".agents/skills/sync-settings"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.readlink(), Path("../../.claude/skills/sync-settings"))
        self.assertEqual((link / "SKILL.md").resolve(), self.skill.resolve())

    def test_entrypoint_and_explicit_selection(self):
        self.assert_contract(
            "name: sync-settings", "Project-local skill shared by Claude and Codex",
            "User instructions take priority", "Validate revisions as commits",
            "Explicit scope replaces automatic boundary discovery",
            "not permission to roll back newer settings",
        )

    def test_history_boundary_and_partial_application(self):
        self.assert_contract(
            "newest to oldest along first-parent history",
            "inspect its diff against its first parent",
            "skipped, never used as a stopping boundary",
            "all applicable effects are verified",
            "Partial application and unknown status are not proof",
            "first fully applied commit", "miss older unapplied changes",
            "ask for a starting commit/range before applying anything",
        )

    def test_safe_source_and_minimal_live_changes(self):
        self.assert_contract(
            "Stop on uncommitted changes", "missing upstream",
            "update only by fast-forward", "Stop on divergence",
            "stop if the source changes while applying",
            "do not replay superseded values",
            "Do not run all of `mac/update`", "exact live write destinations",
            "preserve machine-local values", "specific live removal explicitly",
        )

    def test_failure_and_independent_verification(self):
        self.assert_contract(
            "stop dependent actions", "Reinspect the environment on the next run",
            "independent read", "needs restart/reload",
            "unverified items", "perform no writes",
            "limited to the checked scope",
            "older changes were not checked and may remain unapplied",
            "Do not commit or push repository changes",
        )
