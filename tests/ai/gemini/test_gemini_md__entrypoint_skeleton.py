import unittest

from support import REPO_ROOT


GEMINI_MD_PATH = REPO_ROOT / "ai/gemini/_GEMINI.md"


class GeminiEntrypointSkeletonTest(unittest.TestCase):
    """Skeleton coverage for ai/gemini/_GEMINI.md — the Gemini entrypoint had
    no owning test file until this one. Mirrors the pattern used for the
    Claude entrypoint (tests/ai/claude/test_claude_md__plan_review_body_output.py):
    pin the file's own load-bearing phrases so a future edit that silently
    drops one is caught, without duplicating prompt_base.md's own tests.
    """

    @classmethod
    def setUpClass(cls):
        cls.gemini_md = GEMINI_MD_PATH.read_text(encoding="utf-8")

    def test_file_exists_and_is_non_empty(self):
        self.assertTrue(GEMINI_MD_PATH.is_file())
        self.assertTrue(self.gemini_md.strip())

    def test_composes_shared_sources_via_file_imports(self):
        for required in (
            "@common/prompt_base.md",
            "@common/genshijin-activate.md",
            "@common/genshijin-file-policy.md",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.gemini_md)

    def test_uses_ask_user_for_confirmation_not_plain_text(self):
        self.assertIn("always use the `ask_user` tool instead of plain text output", self.gemini_md)

    def test_language_rule_forces_japanese_responses(self):
        self.assertIn("ALL responses MUST be in Japanese", self.gemini_md)

    def test_slash_command_failsafe_recovers_exactly_once(self):
        # gemini-cliの既知のレース（カスタムコマンドの非同期ロード中に初期プロンプトが
        # 処理されうる）でスラッシュコマンド展開が失敗した際、Failsafeは「停止するだけ」
        # から「1回だけ自力復旧する」へ変わった。無限リトライ化しないことをピン留めする。
        self.assertIn("once, and only once", self.gemini_md)
        self.assertIn("Do not attempt a second recovery", self.gemini_md)

    def test_slash_command_failsafe_reads_command_toml_directly(self):
        self.assertIn("~/.gemini/commands/<command>.toml", self.gemini_md)

    def test_slash_command_failsafe_warns_runtime_includes_do_not_fire(self):
        self.assertIn("!{cat <path>}", self.gemini_md)
        self.assertIn("do not fire on this path", self.gemini_md)

    def test_slash_command_failsafe_writes_failure_to_output_file(self):
        # 第3層（マージ側の側面防御）はこの書き出し指示に依存する。ここが消えると
        # 復旧失敗時にgemini.mdが生成されず、review-merge待ちが最大7200秒ブロックされる
        self.assertIn("AI_REVIEW_OUTPUT_FILE", self.gemini_md)
        self.assertIn("write the failure to that path", self.gemini_md)

    def test_slash_command_failsafe_condition_is_not_limited_to_bare_command(self):
        # 否定ピン: 旧文言「consists solely of a raw slash command」は自然文埋め込み
        # （Codex方式）採用後は成立しない発動条件。この文言が復活すると、pr-review系の
        # 起動文字列（PR番号を含む自然文が後続する形）でFailsafeが発動しなくなる
        self.assertNotIn("consists solely of a raw slash command", self.gemini_md)

    def test_plan_approval_requires_full_plan_content_in_the_same_message(self):
        # Negative-pin rationale: this is the Gemini analogue of the body-output
        # fix just added to Claude's _CLAUDE.md (plan text must be shown before
        # asking for approval, not just approval requested blind). Gemini
        # already states this rule; pin it so a future edit cannot drop it
        # without a failing test, since dropping it would reopen the same
        # "approve before reading" gap this session fixed for Claude.
        for required in (
            "you MUST always output the full markdown content of the plan in the same message",
            "Do not ask for approval or verification without showing the full details of the plan",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.gemini_md)


if __name__ == "__main__":
    unittest.main()
