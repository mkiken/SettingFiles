import unittest

from support import REPO_ROOT


CORE_PATH = REPO_ROOT / "ai/common/review_post_core.md"
CODEX_SKILL_PATH = REPO_ROOT / "ai/codex/skills/review-post/SKILL.md"
CLAUDE_SKILL_PATH = REPO_ROOT / "ai/claude/skills/review-post/SKILL.md"
MECHANICS_PATH = REPO_ROOT / "ai/common/pr_post_mechanics_core.md"


class ReviewPostInlineBodyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = CORE_PATH.read_text(encoding="utf-8")

    def test_summary_block_is_removed_only_from_leading_source_text(self):
        for required in (
            'starts with the exact heading `## レビューサマリー`',
            "Retain the next H2 heading and all later text.",
            "appears anywhere else, or no next H2 heading exists, stop before confirmation",
            "never guess a deletion boundary",
            "inline or individual-fallback finding body",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_attribution_uses_exact_full_name_mapping_and_preflight(self):
        for required in (
            'if . == "claude" then "Claude"',
            'elif . == "gemini" then "Gemini"',
            'elif . == "codex" then "Codex"',
            'else error("unknown review source AI")',
            '"_指摘元: " + join(", ") + "_"',
            "do not abbreviate, capitalize heuristically, or infer names",
            "a final line different from `expected_attribution`",
            "This rejects `_指摘元: C_`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_top_level_summary_remains_in_posting_mechanics(self):
        mechanics = MECHANICS_PATH.read_text(encoding="utf-8")
        self.assertIn("Generate a 1-3 sentence Japanese review summary", mechanics)
        self.assertIn("Keep the merged one-line `summary` and the top-level 1–3 sentence review summary", self.core)

    def test_claude_runtime_and_generated_codex_skill_receive_the_contract(self):
        claude_skill = CLAUDE_SKILL_PATH.read_text(encoding="utf-8")
        codex_skill = CODEX_SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("review_post_core.md", claude_skill)
        self.assertIn(self.core, codex_skill)

    def test_confirmation_is_asked_only_when_target_looks_unexpected(self):
        for required in (
            "`gh pr view <PR_NUMBER> --json number,url,state` fails",
            "`number` or `url` differs from `pr_number` or `pr_url` in merged.json",
            "The target PR `state` is not `OPEN`.",
            "moved past `head_ref_oid` and the re-anchoring check changed any selected item's line",
            "Ask for the ordinary confirmation instead, stating the reason in the preview",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_default_skips_confirmation_but_preserves_preview_validation_and_exception_decisions(self):
        for required in (
            "ordinary confirmation is skipped for `review-post` by default",
            "Always show the selected-item preview and validate",
            "post exactly the displayed selection without waiting for confirmation",
            "Keep the user's decision on already-addressed candidates",
            "confirmation before submitting an existing PENDING review",
            "any validation failure, or post-verification",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)
        self.assertNotIn("Own-PR", self.core)
        self.assertNotIn("--json author,url", self.core)

    def test_adapters_condition_confirmation_on_shared_confirmation_rule(self):
        for path in (
            CLAUDE_SKILL_PATH,
            CODEX_SKILL_PATH,
            CODEX_SKILL_PATH.with_name("skill_head.md"),
        ):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("core's Final Posting Confirmation rule", text)
                self.assertNotIn("Own-PR", text)
                self.assertNotIn(
                    "For the final posting confirmation, ask the user directly and wait for the reply.",
                    text,
                )


if __name__ == "__main__":
    unittest.main()
