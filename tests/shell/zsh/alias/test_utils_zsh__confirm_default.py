"""shell/zsh/alias/utils.zsh の confirm() デフォルト挙動の単体テスト。

confirm() は元々 default_yes=true で、空入力（Enter のみ）でも yes 扱いになる
既知の危険なデフォルトを持っていた（--default-no を明示しない限り破壊的操作が
無入力で進行してしまう）。これを default_yes=false に反転し、yes デフォルトへの
オプトインを --yes フラグに切り替えた。この反転を pin し、あわせて
「message とフラグの引数順序に依存しない」「未知フラグ/複数メッセージ引数は
エラー」という新しい引数パースの不変条件も固定する。
"""
import subprocess
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

STUBS = (
    '_start_prompt_wait_notification() { :; }\n'
    '_finish_prompt_wait_notification() { :; }\n'
)


def run_confirm(args: str, stdin_text: str) -> subprocess.CompletedProcess:
    script = (
        f"{STUBS}"
        'source shell/zsh/alias/utils.zsh; '
        f"confirm {args}"
    )
    return subprocess.run(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env=sanitized_env(HOME="/nonexistent"),
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
    )


class ConfirmDefaultTest(unittest.TestCase):
    def test_empty_input_without_flags_is_no(self):
        result = run_confirm('"続行しますか?"', "\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_lowercase_y_without_flags_is_yes(self):
        result = run_confirm('"続行しますか?"', "y\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_uppercase_y_without_flags_is_yes(self):
        result = run_confirm('"続行しますか?"', "Y\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_n_without_flags_is_no(self):
        result = run_confirm('"続行しますか?"', "n\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_garbage_input_without_flags_is_no(self):
        result = run_confirm('"続行しますか?"', "foo\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_default_prompt_hint_is_y_slash_capital_n(self):
        result = run_confirm('"続行しますか?"', "n\n")
        self.assertIn("[y/N]", result.stdout)

    def test_yes_flag_empty_input_is_yes(self):
        result = run_confirm('"続行しますか?" --yes', "\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_yes_flag_n_is_no(self):
        result = run_confirm('"続行しますか?" --yes', "n\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_yes_flag_garbage_is_no(self):
        result = run_confirm('"続行しますか?" --yes', "foo\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_yes_flag_prompt_hint_is_capital_y_slash_n(self):
        result = run_confirm('"続行しますか?" --yes', "n\n")
        self.assertIn("[Y/n]", result.stdout)

    # --single-key は `read -k 1` で実端末を要求するため、パイプ入力の
    # サブプロセスでは "not interactive and can't open terminal" になり
    # 検証できない（tests/ 内に read -k を対話的に検証している既存テストもない）。
    # ここでは default_yes に影響しないこと（単に single_key フラグを立てる
    # だけで、反転後のデフォルト No を変えないこと）をソースで確認する。
    def test_single_key_does_not_set_default_yes(self):
        confirm_src = (REPO_ROOT / "shell/zsh/alias/utils.zsh").read_text(encoding="utf-8")
        self.assertIn("--single-key)         single_key=true ;;", confirm_src)

    def test_message_flag_order_is_independent(self):
        # message を先頭に固定する必要はない: --yes を先に置いても同じ結果になる
        result = run_confirm('--yes "続行しますか?"', "\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_default_no_flag_is_rejected(self):
        # 廃止した --default-no を渡すと、黙って無視せずエラーで落ちる
        result = run_confirm('"続行しますか?" --default-no', "\n")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_unknown_flag_is_rejected(self):
        result = run_confirm('"続行しますか?" --typo-flag', "\n")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_multiple_message_arguments_are_rejected(self):
        result = run_confirm('"続行しますか?" "もう一つ"', "\n")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_missing_message_argument_is_rejected(self):
        result = run_confirm('--yes', "\n")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_no_cancel_msg_suppresses_cancel_message(self):
        result = run_confirm('"続行しますか?" --no-cancel-msg', "n\n")
        self.assertNotIn("❌ キャンセルされました", result.stdout)

    def test_default_shows_cancel_message(self):
        result = run_confirm('"続行しますか?"', "n\n")
        self.assertIn("❌ キャンセルされました", result.stdout)


if __name__ == "__main__":
    unittest.main()
