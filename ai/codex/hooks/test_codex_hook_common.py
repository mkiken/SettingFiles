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

    def test_detects_message_ending_with_question_mark(self):
        self.assertTrue(assistant_response_needs_user_input("この方針で進めてよろしいですか？"))

    def test_ignores_completion_summary(self):
        message = "実装した。テストも通過した。変更はコミットしていない。"

        self.assertFalse(assistant_response_needs_user_input(message))


if __name__ == "__main__":
    unittest.main()
