import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

WRAPPER = REPO_ROOT / "shell/tmux/herdr-popup-run.sh"

# 子プロセスが自身の見た環境や引数を記録するためのstub。
# 第1引数として指定した終了コードでexitし、任意でHERDR_POPUP_PAUSE_MARKへ書き込む。
CHILD_STUB = """#!/bin/bash
printf '%s\\n' "$@" > "$CHILD_ARGV_LOG"
: > "$CHILD_ENV_LOG"
printf 'HERDR_POPUP_COMMAND=%s\\n' "${HERDR_POPUP_COMMAND:-}" >> "$CHILD_ENV_LOG"
printf 'HERDR_POPUP_WRAPPED=%s\\n' "${HERDR_POPUP_WRAPPED:-}" >> "$CHILD_ENV_LOG"
printf 'LANG=%s\\n' "${LANG:-}" >> "$CHILD_ENV_LOG"
printf 'HERDR_POPUP_PAUSE_MARK=%s\\n' "${HERDR_POPUP_PAUSE_MARK:-}" >> "$CHILD_ENV_LOG"
if [[ -n "${CHILD_WRITE_MARK:-}" && -n "${HERDR_POPUP_PAUSE_MARK:-}" ]]; then
    printf 'marked\\n' >> "$HERDR_POPUP_PAUSE_MARK"
fi
if [[ -n "${CHILD_ECHO_MARK_PATH:-}" ]]; then
    printf '%s\\n' "${HERDR_POPUP_PAUSE_MARK:-}" > "$CHILD_MARK_PATH_LOG"
fi
exit "${CHILD_EXIT:-0}"
"""


def run_wrapper(
    argv: list[str],
    *,
    child_exit: int = 0,
    child_write_mark: bool = False,
    child_echo_mark_path: bool = False,
    lang: str | None = None,
    stdin=None,
    timeout: float = 10,
) -> tuple[subprocess.CompletedProcess, dict]:
    """herdr-popup-run.shをstub子プロセス付きで実行し、(結果, 観測ログ) を返す。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        child = temp_path / "child_stub.sh"
        child.write_text(CHILD_STUB)
        child.chmod(0o755)

        argv_log = temp_path / "argv.log"
        env_log = temp_path / "env.log"
        mark_path_log = temp_path / "mark_path.log"

        env = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": temp_dir,
            "TMPDIR": temp_dir,
            "CHILD_ARGV_LOG": str(argv_log),
            "CHILD_ENV_LOG": str(env_log),
            "CHILD_MARK_PATH_LOG": str(mark_path_log),
            "CHILD_EXIT": str(child_exit),
        }
        if child_write_mark:
            env["CHILD_WRITE_MARK"] = "1"
        if child_echo_mark_path:
            env["CHILD_ECHO_MARK_PATH"] = "1"
        if lang is not None:
            env["LANG"] = lang

        resolved_argv = [str(child) if a == "__CHILD__" else a for a in argv]

        result = subprocess.run(
            ["bash", str(WRAPPER), *resolved_argv],
            cwd=REPO_ROOT,
            env=env,
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        observed = {
            "argv": argv_log.read_text() if argv_log.exists() else None,
            "env": env_log.read_text() if env_log.exists() else None,
            "mark_path": mark_path_log.read_text().strip() if mark_path_log.exists() else None,
        }
        return result, observed


class HerdrPopupRunExitCodeTest(unittest.TestCase):
    def test_exit_zero_does_not_pause(self):
        result, _ = run_wrapper(["__CHILD__"], child_exit=0, stdin="")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("何かキーを押すと閉じます", result.stderr)

    def test_exit_sigint_does_not_pause(self):
        result, _ = run_wrapper(["__CHILD__"], child_exit=130, stdin="")
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("何かキーを押すと閉じます", result.stderr)

    def test_exit_one_pauses_and_reports_code(self):
        result, _ = run_wrapper(["__CHILD__"], child_exit=1, stdin="")
        self.assertEqual(result.returncode, 1)
        self.assertIn("エラーで終了しました", result.stderr)
        self.assertIn("exit 1", result.stderr)
        self.assertIn("何かキーを押すと閉じます", result.stderr)

    def test_exit_42_reports_exact_code(self):
        result, _ = run_wrapper(["__CHILD__"], child_exit=42, stdin="")
        self.assertEqual(result.returncode, 42)
        self.assertIn("exit 42", result.stderr)

    def test_exit_127_pauses(self):
        result, _ = run_wrapper(["__CHILD__"], child_exit=127, stdin="")
        self.assertEqual(result.returncode, 127)
        self.assertIn("何かキーを押すと閉じます", result.stderr)


class HerdrPopupRunArgvTest(unittest.TestCase):
    def test_argv_with_spaces_and_quotes_is_not_re_split(self):
        # evalしていないことの固定: 空白/クォートを含む引数がそのまま1引数として届く
        result, observed = run_wrapper(
            ["__CHILD__", "echo \"a b\"", "second arg"], child_exit=0, stdin=""
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(observed["argv"], 'echo "a b"\nsecond arg\n')

    def test_no_args_reports_usage(self):
        result = subprocess.run(
            ["bash", str(WRAPPER)],
            cwd=REPO_ROOT,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no command given", result.stderr)


class HerdrPopupRunEnvTest(unittest.TestCase):
    def test_exports_popup_command_gate(self):
        _, observed = run_wrapper(["__CHILD__"], child_exit=0, stdin="")
        self.assertIn("HERDR_POPUP_COMMAND=1", observed["env"])

    def test_exports_wrapped_pause_contract_variable(self):
        _, observed = run_wrapper(["__CHILD__"], child_exit=0, stdin="")
        self.assertIn("HERDR_POPUP_WRAPPED=1", observed["env"])

    def test_lang_fallback_when_unset(self):
        _, observed = run_wrapper(["__CHILD__"], child_exit=0, lang=None, stdin="")
        self.assertIn("LANG=en_US.UTF-8", observed["env"])

    def test_lang_not_overridden_when_set(self):
        _, observed = run_wrapper(["__CHILD__"], child_exit=0, lang="ja_JP.UTF-8", stdin="")
        self.assertIn("LANG=ja_JP.UTF-8", observed["env"])

    def test_pause_mark_path_is_exported_and_exists_during_run(self):
        _, observed = run_wrapper(
            ["__CHILD__"], child_exit=0, child_echo_mark_path=True, stdin=""
        )
        self.assertTrue(observed["mark_path"])


class HerdrPopupRunPauseMarkTest(unittest.TestCase):
    def test_individual_pause_suppresses_wrapper_pause(self):
        result, _ = run_wrapper(
            ["__CHILD__"], child_exit=1, child_write_mark=True, stdin=""
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("何かキーを押すと閉じます", result.stderr)

    def test_missing_mark_falls_back_to_wrapper_pause(self):
        result, _ = run_wrapper(
            ["__CHILD__"], child_exit=1, child_write_mark=False, stdin=""
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("何かキーを押すと閉じます", result.stderr)

    def test_success_with_mark_still_does_not_pause(self):
        result, _ = run_wrapper(
            ["__CHILD__"], child_exit=0, child_write_mark=True, stdin=""
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("何かキーを押すと閉じます", result.stderr)


class HerdrPopupRunCleanupTest(unittest.TestCase):
    def test_mark_file_removed_after_success(self):
        _, observed = run_wrapper(
            ["__CHILD__"], child_exit=0, child_echo_mark_path=True, stdin=""
        )
        mark_path = Path(observed["mark_path"])
        self.assertFalse(mark_path.exists())

    def test_mark_file_removed_after_error_pause(self):
        _, observed = run_wrapper(
            ["__CHILD__"], child_exit=1, child_echo_mark_path=True, stdin=""
        )
        mark_path = Path(observed["mark_path"])
        self.assertFalse(mark_path.exists())


class HerdrPopupRunNoTtyTest(unittest.TestCase):
    def test_no_tty_does_not_hang_and_still_reports(self):
        # stdinをDEVNULL相当（空文字入力）にしてもハングしないこと。
        # tty無し環境なのでread -rsn1 </dev/ttyがエラーで即座に諦める前提。
        result, _ = run_wrapper(["__CHILD__"], child_exit=1, stdin="", timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("何かキーを押すと閉じます", result.stderr)


if __name__ == "__main__":
    unittest.main()
