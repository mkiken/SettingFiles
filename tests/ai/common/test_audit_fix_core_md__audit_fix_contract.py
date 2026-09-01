import unittest

from support import REPO_ROOT

CORE_PATH = REPO_ROOT / "ai/common/audit_fix_core.md"
DESIGNER_PATH = REPO_ROOT / "ai/common/audit_fix_subagents/designer_core.md"
IMPLEMENTER_PATH = REPO_ROOT / "ai/common/audit_fix_subagents/implementer_core.md"
CLAUDE_SKILL_PATH = REPO_ROOT / "ai/claude/skills/audit-fix/SKILL.md"
CODEX_HEAD_PATH = REPO_ROOT / "ai/codex/skills/audit-fix/skill_head.md"
CODEX_SKILL_PATH = REPO_ROOT / "ai/codex/skills/audit-fix/SKILL.md"
GEMINI_COMMAND_PATH = REPO_ROOT / "ai/gemini/commands/audit-fix.toml"
SERVER_PATH = REPO_ROOT / "shell/common/pr/serve_review_report.py"

DECISIONS = ("apply", "dismiss")
GROUP_STATUSES = (
    "pending",
    "designing",
    "designed",
    "approved",
    "waiting",
    "implementing",
    "applied",
    "skipped",
    "failed",
)
ITEM_STATUSES = ("pending", "applied", "skipped", "failed")
ADAPTERS = {
    "claude": CLAUDE_SKILL_PATH,
    "codex": CODEX_HEAD_PATH,
    "gemini": GEMINI_COMMAND_PATH,
}


class AuditFixContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = CORE_PATH.read_text(encoding="utf-8")
        cls.designer = DESIGNER_PATH.read_text(encoding="utf-8")
        cls.implementer = IMPLEMENTER_PATH.read_text(encoding="utf-8")
        cls.server = SERVER_PATH.read_text(encoding="utf-8")

    def test_decision_vocabulary_agrees_with_the_server_audit_profile(self):
        for decision in DECISIONS:
            with self.subTest(decision=decision):
                self.assertIn(f'"{decision}"', self.core)
                self.assertIn(f'"{decision}"', self.server)

    def test_review_decisions_are_absent_from_the_core(self):
        # レビュー側の判断値を前提にすると audit プロファイルの state.json を誤読する
        for decision in ("fix", "post"):
            with self.subTest(decision=decision):
                self.assertNotIn(f'"{decision}"', self.core)

    def test_audit_schema_version_agrees_between_core_and_server(self):
        self.assertIn('"schema_version": 1', self.core)
        self.assertIn('"schema_version": 1', self.server)

    def test_core_never_writes_the_browser_owned_state(self):
        self.assertIn("the browser owns it", self.core)
        self.assertIn("Never write `<RUN_DIR>/state.json`", self.core)

    def test_core_keeps_the_item_number_fallback_closed(self):
        # config-audit から撤去した番号打ち返し方式が後継スキル側から復活しないためのピン
        self.assertIn("never ask the user for item numbers", self.core)
        self.assertIn("Never fall back to asking for item numbers", self.core)

    def test_core_pins_the_quote_and_ordering_contract(self):
        self.assertIn("byte for byte", self.core)
        self.assertIn("bottom up", self.core)

    def test_core_declares_the_cross_track_dependency_rule(self):
        self.assertIn("depends_on", self.core)
        self.assertIn("closure", self.core)

    def test_selection_confirmation_warns_about_selected_risks_only(self):
        for token in ("selected items whose `risk` is an object", "#id summary — reason", "risk未評価"):
            with self.subTest(token=token):
                self.assertIn(token, self.core)
        self.assertIn("warning-only", self.core)
        self.assertIn("do not dismiss, block, or\nask an additional confirmation", self.core)

    def test_core_declares_every_apply_state_status(self):
        for status in GROUP_STATUSES:
            with self.subTest(group_status=status):
                self.assertIn(status, self.core)
        for status in ITEM_STATUSES:
            with self.subTest(item_status=status):
                self.assertIn(status, self.core)

    def test_core_has_no_worktree_or_commit_machinery(self):
        # 監査対象は ~/.claude/CLAUDE.md など git 管理外を含むため worktree 前提が
        # 成立しない。review-fix からの機構コピペ混入を防ぐ（コア本文は不採用の
        # 理由として "worktree" の語自体には触れるので、道具立ての不在で検査する）
        for token in ("wtc", "wtm", "git merge", "WORKTREE_TASK_DOC", "commit_merge"):
            with self.subTest(token=token):
                self.assertNotIn(token, self.core)
        self.assertIn("no worktrees", self.core)
        self.assertIn("Do not commit", self.core)

    def test_every_adapter_resolves_its_own_audit_run_dir(self):
        for platform, path in ADAPTERS.items():
            with self.subTest(platform=platform):
                text = path.read_text(encoding="utf-8")
                self.assertIn("ai_audit_run_dir.sh --latest", text)
                # レビュー側の run dir を掴むと merged.json を audit として読んでしまう
                self.assertNotIn("ai_review_run_dir.sh", text)

    def test_claude_adapter_pins_the_orchestrator_model_and_can_apply(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        for token in ("model: sonnet", "Edit", "Write", "Task"):
            with self.subTest(token=token):
                self.assertIn(token, claude_skill)

    def test_claude_adapter_names_the_generated_agents(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("subagent_type `audit-fix-designer` / `audit-fix-implementer`", claude_skill)
        # general-purpose は呼び出し元のモデルを継承するため、指定するとロール別
        # モデル固定が消える。アダプタは代用禁止として言及するだけに留める
        self.assertIn("never substitute `general-purpose`", claude_skill)
        self.assertNotIn("subagent_type: general-purpose", claude_skill)

    def test_codex_adapter_names_the_registered_agents_and_depth_limit(self):
        codex_head = CODEX_HEAD_PATH.read_text(encoding="utf-8")
        self.assertIn("audit_fix_designer", codex_head)
        self.assertIn("audit_fix_implementer", codex_head)
        self.assertIn("max_depth 1", codex_head)

    def test_gemini_adapter_declares_its_edit_and_confirmation_primitives(self):
        gemini_command = GEMINI_COMMAND_PATH.read_text(encoding="utf-8")
        for token in ("replace", "write_file", "ask_user", "audit-fix-designer"):
            with self.subTest(token=token):
                self.assertIn(token, gemini_command)

    def test_claude_runtime_and_generated_codex_skill_receive_the_core(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        codex_skill = CODEX_SKILL_PATH.read_text(encoding="utf-8")
        gemini_command = GEMINI_COMMAND_PATH.read_text(encoding="utf-8")
        self.assertIn("audit_fix_core.md", claude_skill)
        self.assertIn("audit_fix_core.md", gemini_command)
        self.assertIn(self.core, codex_skill)

    def test_designer_and_implementer_split_their_write_permissions(self):
        self.assertIn("never modify", self.designer)
        self.assertIn("no apply_state.json, no state.json", self.designer)
        # implementer が audit.json を読むと設計を無視して自前判断を始めうる
        self.assertNotIn("audit.json`", self.implementer.split("# Task")[0])
        self.assertIn("Do not read audit.json or state.json", self.implementer)

    def test_designer_grounds_its_rewrite_in_the_audit_detail_labels(self):
        for label in ("改善案", "短縮案", "問題点", "内容A", "推奨"):
            with self.subTest(label=label):
                self.assertIn(label, self.designer)

    def test_core_payloads_match_the_role_cores(self):
        for placeholder in ("<RUN_DIR>", "<GROUP_ID>", "<DESIGN_FILE>"):
            with self.subTest(placeholder=placeholder):
                self.assertIn(placeholder, self.designer)
                self.assertIn(placeholder, self.implementer)
        for placeholder in ("<TARGET_FILES>", "<ITEM_IDS>"):
            with self.subTest(placeholder=placeholder):
                self.assertIn(placeholder, self.designer)

    def test_role_cores_stay_safe_for_the_codex_toml_literal(self):
        # 生成器は ''' を検出して失敗するので、ソース側で混入を防ぐ
        for name, text in (("designer", self.designer), ("implementer", self.implementer)):
            with self.subTest(role=name):
                self.assertNotIn("'''", text)


if __name__ == "__main__":
    unittest.main()
