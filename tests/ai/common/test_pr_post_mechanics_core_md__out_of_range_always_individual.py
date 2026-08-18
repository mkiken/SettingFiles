import unittest

from support import REPO_ROOT


MECHANICS_PATH = REPO_ROOT / "ai/common/pr_post_mechanics_core.md"
CORE_PATH = REPO_ROOT / "ai/common/review_post_core.md"
CODEX_REVIEW_POST_PATH = REPO_ROOT / "ai/codex/skills/review-post/SKILL.md"
CODEX_PR_COMMENT_POST_PATH = REPO_ROOT / "ai/codex/skills/pr-comment-post/SKILL.md"


class OutOfRangeAlwaysIndividualTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mechanics = MECHANICS_PATH.read_text(encoding="utf-8")
        cls.core = CORE_PATH.read_text(encoding="utf-8")
        cls.codex_review_post = CODEX_REVIEW_POST_PATH.read_text(encoding="utf-8")
        cls.codex_pr_comment_post = CODEX_PR_COMMENT_POST_PATH.read_text(
            encoding="utf-8"
        )

    def test_three_way_confirmation_wording_is_removed(self):
        # diff範囲外項目の扱いをユーザーに確認する3択（畳み込み/個別投稿/破棄）は
        # 意図的に廃止した。復活させると常に個別投稿という仕様が崩れる。
        forbidden = (
            "fold them into the review body",
            "or drop them",
            "ask the user how to handle",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.mechanics)

    def test_individual_posting_is_unconditional(self):
        # 「ユーザーが個別投稿を選んだ場合」という条件節も廃止済み。
        # 残っていると常時個別投稿の意図が伝わらない。
        self.assertNotIn(
            "When the user chooses individual general comments", self.mechanics
        )

    def test_preview_marker_indicates_individual_posting(self):
        self.assertIn("※diff範囲外（個別コメントで投稿）", self.mechanics)

    def test_post_verification_procedure_is_preserved(self):
        for required in (
            "issues/comments/{comment_id}",
            "require the body to match exactly",
            "Do not collapse multiple findings into one general comment",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.mechanics)

    def test_ordering_constraint_is_preserved(self):
        self.assertIn("after the inline review succeeds", self.mechanics)

    def test_review_api_safety_rule_is_preserved(self):
        self.assertIn(
            "Never send an unverified out-of-range item to the Review API.",
            self.mechanics,
        )

    def test_final_report_separates_inline_and_individual_counts(self):
        self.assertIn(
            "Report inline-review comment count and out-of-range individual-comment "
            "count separately.",
            self.mechanics,
        )

    def test_codex_generated_skills_stay_in_sync(self):
        for generated in (self.codex_review_post, self.codex_pr_comment_post):
            with self.subTest():
                self.assertNotIn("fold them into the review body", generated)
                self.assertNotIn("or drop them", generated)
                self.assertNotIn(
                    "When the user chooses individual general comments", generated
                )
                self.assertIn("※diff範囲外（個別コメントで投稿）", generated)
                self.assertIn("issues/comments/{comment_id}", generated)

    def test_review_post_core_tilde_prefix_note_is_unchanged(self):
        # ~prefix (pre-existing-code anchor) の扱いはこの変更の対象外。
        # review_post_core.mdの記述が変わっていないことを確認する。
        self.assertIn(
            "Items whose `line_spec` starts with `~` are pre-existing-code anchors "
            "and cannot be inline comments",
            self.core,
        )


if __name__ == "__main__":
    unittest.main()
