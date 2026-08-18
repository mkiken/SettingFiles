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
