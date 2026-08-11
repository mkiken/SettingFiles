import unittest

from support import REPO_ROOT


CORE = REPO_ROOT / "ai/common/pr_comment_implement_core.md"


class PrCommentImplementStandaloneReplyHeaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

    def test_reference_variables_are_defined(self):
        for variable in ("REPLY_REF_URL", "REPLY_REF_SUMMARY", "REPLY_REF_LOCATION"):
            with self.subTest(variable=variable):
                self.assertIn(variable, self.content)

    def test_header_uses_blockquote_link_format(self):
        self.assertIn("> 返信対象: [{one-line paraphrase}]({REPLY_REF_URL})", self.content)

    def test_header_is_scoped_to_standalone_not_thread(self):
        standalone_rule = self.content.index("When `REPLY_PATH=standalone`, prepend a reference header")
        thread_omit = self.content.index(
            "For `REPLY_PATH=thread`, omit this header entirely", standalone_rule
        )
        # The omit clause for thread must appear inside the same rule block,
        # not as a separate unconditional instruction elsewhere.
        self.assertLess(standalone_rule, thread_omit)
        self.assertLess(thread_omit - standalone_rule, 2000)

    def test_issuecomment_branch_captures_reference_info(self):
        issuecomment_branch = self.content.index("Extract `ISSUE_COMMENT_ID`")
        capture_note = self.content.index(
            "Whenever a branch above sets `REPLY_PATH=standalone`"
        )
        fetch_snippet = self.content.index("ISSUE_COMMENT_JSON=")

        self.assertGreater(issuecomment_branch, 0)
        self.assertGreater(capture_note, 0)
        self.assertIn("REPLY_REF_URL=", self.content[fetch_snippet:fetch_snippet + 400])

    def test_review_branches_set_reply_ref_url(self):
        zero_comment_branch = self.content.index("0: treat the review as standalone")
        finding_branch = self.content.index(
            "when `PROMPT` identifies a finding"
        )

        zero_comment_contract = self.content[zero_comment_branch:finding_branch]
        self.assertIn("REPLY_REF_URL", zero_comment_contract)
        self.assertIn("REPLY_REF_LOCATION` unset", zero_comment_contract)

        finding_contract = self.content[finding_branch:finding_branch + 1200]
        self.assertIn("REPLY_REF_URL", finding_contract)
        self.assertIn("REPLY_REF_LOCATION", finding_contract)

    def test_thread_downgrade_reprepends_header(self):
        downgrade_note = self.content.index("On standalone downgrade, the reply body")
        self.assertIn(
            "prepend one now, following Phase 5's",
            self.content[downgrade_note:downgrade_note + 300],
        )
        self.assertIn(
            "kept from Phase 1's target-comment fetch" .replace(" ", " "),
            self.content[downgrade_note:downgrade_note + 400].replace("\n", " "),
        )

    def test_auxiliary_info_omission_rule_is_stated(self):
        self.assertIn("omit the entire second line when nothing is", self.content)
        self.assertIn("Never emit a placeholder for a value that wasn't captured", self.content)

    def test_paraphrase_rule_forbids_verbatim_copy(self):
        self.assertIn("never paste the raw text verbatim", self.content)
        self.assertIn("compress its point to one line", self.content)

    def test_codex_generated_skill_carries_the_same_header_contract(self):
        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "> 返信対象: [{one-line paraphrase}]({REPLY_REF_URL})", codex_skill
        )
        self.assertIn("Never emit a placeholder for a value that wasn't captured", codex_skill)

    def test_claude_and_gemini_adapters_reference_core_without_duplicating_header(self):
        claude_skill = (
            REPO_ROOT / "ai/claude/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")
        gemini_command = (
            REPO_ROOT / "ai/gemini/commands/pr-comment-implement.toml"
        ).read_text(encoding="utf-8")

        self.assertIn("~/.claude/common/pr_comment_implement_core.md", claude_skill)
        self.assertIn("~/.gemini/common/pr_comment_implement_core.md", gemini_command)
        self.assertNotIn("返信対象", claude_skill)
        self.assertNotIn("返信対象", gemini_command)


if __name__ == "__main__":
    unittest.main()
