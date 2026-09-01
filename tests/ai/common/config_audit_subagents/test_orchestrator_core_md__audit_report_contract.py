import unittest

from support import REPO_ROOT

CORE_PATH = REPO_ROOT / "ai/common/config_audit_subagents/orchestrator_core.md"
CLAUDE_SKILL_PATH = REPO_ROOT / "ai/claude/skills/config-audit/SKILL.md"
CODEX_SKILL_PATH = REPO_ROOT / "ai/codex/skills/config-audit/SKILL.md"
GEMINI_COMMAND_PATH = REPO_ROOT / "ai/gemini/commands/config-audit.toml"
RENDERER_PATH = REPO_ROOT / "shell/common/pr/generate_audit_report.py"
SERVER_PATH = REPO_ROOT / "shell/common/pr/serve_review_report.py"

CATEGORIES = ("default", "overlap", "patch", "ambiguity", "concise", "conflict")
DECISIONS = ("apply", "dismiss")
AUDIT_SCHEMA_VERSION = 1


class AuditReportContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = CORE_PATH.read_text(encoding="utf-8")
        cls.renderer = RENDERER_PATH.read_text(encoding="utf-8")
        cls.server = SERVER_PATH.read_text(encoding="utf-8")

    def test_every_category_is_declared_in_core_and_renderer(self):
        # 片方に無いカテゴリはHTML上で生文字列フォールバック表示になる
        for category in CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(f"`{category}`", self.core)
                self.assertIn(f'"{category}"', self.renderer)

    def test_every_decision_is_declared_in_core_renderer_and_server(self):
        for decision in DECISIONS:
            with self.subTest(decision=decision):
                self.assertIn(f'"{decision}"', self.core)
                self.assertIn(f'"{decision}"', self.renderer)
                self.assertIn(f'"{decision}"', self.server)

    def test_review_decisions_are_absent_from_the_audit_renderer(self):
        # レビュー側の判断値が混ざるとサーバーのauditプロファイルに拒否される
        for decision in ("fix", "post"):
            with self.subTest(decision=decision):
                self.assertNotIn(f'["{decision}"', self.renderer)

    def test_audit_schema_version_agrees_between_core_and_server(self):
        self.assertIn(f'"schema_version": {AUDIT_SCHEMA_VERSION}', self.core)
        self.assertIn(f'"schema_version": {AUDIT_SCHEMA_VERSION}', self.server)

    def test_core_names_the_report_pipeline(self):
        for token in ("generate_audit_report.py", "serve_review_report.py", "audit-report", "audit.json"):
            with self.subTest(token=token):
                self.assertIn(token, self.core)

    def test_core_forbids_printing_the_report_and_writing_state(self):
        self.assertIn("Do not print the report body", self.core)
        self.assertIn("the browser owns it", self.core)

    def test_core_requires_server_verification_before_opening_a_browser(self):
        self.assertIn("without** `--open`", self.core)
        self.assertIn("exactly once", self.core)

    def test_core_no_longer_asks_for_item_numbers(self):
        # 番号打ち返し方式の撤去が本変更の目的。フォールバックの復活を防ぐ
        self.assertIn("Never fall back to asking for item numbers", self.core)
        self.assertNotIn("番号指定で部分適用", self.core)
        self.assertNotIn("依存: 項目", self.core)

    def test_dependency_contract_uses_depends_on(self):
        self.assertIn("depends_on", self.core)
        self.assertIn("symmetric", self.core)
        self.assertIn("depends_on", self.renderer)

    def test_each_adapter_declares_its_own_run_dir_and_platform_key(self):
        adapters = {
            "claude": CLAUDE_SKILL_PATH,
            "codex": REPO_ROOT / "ai/codex/skills/config-audit/skill_head.md",
            "gemini": GEMINI_COMMAND_PATH,
        }
        for platform, path in adapters.items():
            with self.subTest(platform=platform):
                text = path.read_text(encoding="utf-8")
                self.assertIn(f"ai_audit_run_dir.sh {platform}", text)
                self.assertIn(f"`platform_key` = `{platform}`", text)

    def test_claude_adapter_dropped_the_scratchpad_exception(self):
        # レポートがブラウザとrun_dirに残るため、scratchpad保存の根拠は消えた
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        self.assertNotIn("scratchpad", claude_skill)
        self.assertNotIn("レポートのファイル保存", claude_skill)

    def test_claude_adapter_can_run_the_pipeline_and_apply_edits(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        for tool in ("Bash(python3:*)", "Bash(bash:*)", "Write", "Edit"):
            with self.subTest(tool=tool):
                self.assertIn(tool, claude_skill)

    def test_claude_runtime_and_generated_codex_skill_receive_the_contract(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        codex_skill = CODEX_SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("config_audit_subagents/orchestrator_core.md", claude_skill)
        self.assertIn(self.core, codex_skill)


if __name__ == "__main__":
    unittest.main()
