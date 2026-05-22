import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_hook_common import assistant_response_needs_user_input


class AssistantResponseNeedsUserInputTest(unittest.TestCase):
    def test_detects_approval_question_followed_by_revision_request(self):
        message = """
        ## 実装設計

        ### 変更方針

        - 変更する振る舞い: なし。テスト網羅性のみ追加
        - 変更しない範囲: validator 本体、エラーメッセージ、既存ケースの期待値

        この設計で実装を進めてよろしいですか？修正点があればお知らせください。
        """

        self.assertTrue(assistant_response_needs_user_input(message))

    def test_detects_question_in_tail_even_when_not_at_end(self):
        message = "実装方針は上記の通り。この設計で進めてよろしいですか？修正点があればお知らせください。"

        self.assertTrue(assistant_response_needs_user_input(message))

    def test_ignores_url_query_in_tail(self):
        message = "確認した。詳細は https://example.com/search?q=codex を参照。"

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_inline_code_question_mark_in_tail(self):
        message = "原因は lazy quantifier の `.+?` にある。修正済み。"

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_fenced_code_question_mark_in_tail(self):
        message = """
        修正した。

        ```python
        pattern = r".+?"
        ```

        テストも通過した。
        """

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_old_question_outside_tail(self):
        message = "この方針で進めてよろしいですか？" + (" 完了。" * 200)

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_completion_summary(self):
        message = "実装した。テストも通過した。変更はコミットしていない。"

        self.assertFalse(assistant_response_needs_user_input(message))


if __name__ == "__main__":
    unittest.main()
