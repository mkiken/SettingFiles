"""shell/tmux/tmux_window_name.py の単体テスト（FakeTmuxランナー注入、実tmux不要）"""
import contextlib
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shell" / "tmux"))

import tmux_emoji
import tmux_window_name as twn

ID = tmux_emoji.EMOJI_ID_CLAUDE  # ✴️
DONE = tmux_emoji.EMOJI_STATUS_COMPLETED  # ✅
WAIT = tmux_emoji.EMOJI_STATUS_NOTIFICATION  # ✋
BUSY = tmux_emoji.EMOJI_STATUS_ONGOING  # 🤖
ALERT = tmux_emoji.EMOJI_CONTEXT_ALERT  # ⚠️

TMUX_ENV = {"TMUX_PANE": "%1", "TERM_PROGRAM": "tmux"}


class FakeTmux:
    """subprocess.run互換の呼び出しを記録し、ウィンドウ名の読み取り・renameを模倣する。"""

    def __init__(self, window_name="", fail_on=()):
        self.window_name = window_name
        self.fail_on = set(fail_on)  # {"name", "window_id", "rename"} の部分集合
        self.calls = []
        self.renamed_to = None

    def __call__(self, cmd, **_kwargs):
        kind = self._kind(cmd)
        self.calls.append(kind)
        if kind in self.fail_on:
            raise subprocess.CalledProcessError(1, cmd)
        if kind == "name":
            return SimpleNamespace(stdout=f"{self.window_name}\n")
        if kind == "window_id":
            return SimpleNamespace(stdout="@5\n")
        if kind == "rename":
            self.renamed_to = cmd[-1]
            return SimpleNamespace(stdout="")
        raise AssertionError(f"unexpected tmux command: {cmd}")

    @staticmethod
    def _kind(cmd):
        if cmd[:2] == ["tmux", "display-message"]:
            return "window_id" if cmd[-1] == "#{window_id}" else "name"
        if cmd[:2] == ["tmux", "rename-window"]:
            return "rename"
        return "unknown"


class TestBuildUpdatedName(unittest.TestCase):
    def test_table(self):
        cases = [
            # (説明, current, status_emoji, identifier, expected)
            ("プレーン名に付与", "main", DONE, ID, f"{ID}{DONE}main"),
            ("状態アイコンのみを置換", f"{BUSY}main", DONE, ID, f"{ID}{DONE}main"),
            ("再更新の冪等性", f"{ID}{BUSY}main", DONE, ID, f"{ID}{DONE}main"),
            ("バッジ保持", f"{ID}{BUSY}{ALERT}main", DONE, ID, f"{ID}{DONE}{ALERT}main"),
            ("バッジ先頭でも重複しない", f"{ALERT}{DONE}main", DONE, ID, f"{ID}{DONE}{ALERT}main"),
            ("identifierなしのshell形式", f"{ALERT}main", WAIT, "", f"{WAIT}{ALERT}main"),
            ("絵文字のみの名前", f"{ID}{BUSY}", DONE, ID, f"{ID}{DONE}"),
            ("空文字境界", "", DONE, ID, f"{ID}{DONE}"),
        ]
        for desc, current, emoji, identifier, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.build_updated_name(current, emoji, identifier), expected)


class TestBuildCleanedName(unittest.TestCase):
    def test_table(self):
        cases = [
            ("状態アイコンを除去", f"{ID}{BUSY}main", "main"),
            ("バッジも含めて除去", f"{ID}{BUSY}{ALERT}main", "main"),
            ("バッジのみでも除去", f"{ALERT}main", "main"),
            ("絵文字なしは不変", "main", "main"),
            ("空文字境界", "", ""),
        ]
        for desc, current, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.build_cleaned_name(current), expected)


class TestGetTmuxPaneId(unittest.TestCase):
    def test_table(self):
        cases = [
            ("環境変数なし", {}, None),
            ("TMUX_PANEのみ", {"TMUX_PANE": "%1"}, None),
            ("TERM_PROGRAM不一致", {"TMUX_PANE": "%1", "TERM_PROGRAM": "vscode"}, None),
            ("tmux内", TMUX_ENV, "%1"),
        ]
        for desc, env, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.get_tmux_pane_id(env), expected)


class TestUpdateTmuxWindowName(unittest.TestCase):
    def test_outside_tmux_spawns_nothing(self):
        fake = FakeTmux()
        code = twn.update_tmux_window_name(twn.HookStatus.ONGOING, ID, run=fake, env={})
        self.assertEqual(code, twn.UPDATE_OK)
        self.assertEqual(fake.calls, [])

    def test_status_and_error_reporting_table(self):
        cases = [
            # (説明, fail_on, expected_code)
            ("名前取得失敗", {"name"}, twn.UPDATE_NAME_READ_FAILED),
            ("window_id取得失敗", {"window_id"}, twn.UPDATE_WINDOW_ID_FAILED),
            ("rename失敗", {"rename"}, twn.UPDATE_RENAME_FAILED),
        ]
        for desc, fail_on, expected_code in cases:
            with self.subTest(desc):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = twn.update_tmux_window_name(
                        twn.HookStatus.ONGOING,
                        ID,
                        report_error=True,
                        run=FakeTmux(window_name="main", fail_on=fail_on),
                        env=TMUX_ENV,
                    )
                self.assertEqual(code, expected_code)
                self.assertEqual(stderr.getvalue(), twn.UPDATE_MESSAGES[expected_code] + "\n")

    def test_name_build_failure_reports_distinct_status(self):
        stderr = io.StringIO()
        with mock.patch.object(twn, "build_updated_name", side_effect=ValueError("invalid")):
            with contextlib.redirect_stderr(stderr):
                code = twn.update_tmux_window_name(
                    BUSY,
                    ID,
                    report_error=True,
                    run=FakeTmux(window_name="main"),
                    env=TMUX_ENV,
                )
        self.assertEqual(code, twn.UPDATE_NAME_BUILD_FAILED)
        self.assertEqual(stderr.getvalue(), twn.UPDATE_MESSAGES[code] + "\n")

    def test_failure_is_silent_without_report_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = twn.update_tmux_window_name(
                BUSY,
                ID,
                run=FakeTmux(window_name="main", fail_on={"rename"}),
                env=TMUX_ENV,
            )
        self.assertEqual(code, twn.UPDATE_RENAME_FAILED)
        self.assertEqual(stderr.getvalue(), "")

    def test_hook_status_and_raw_emoji_are_equivalent(self):
        by_status, by_emoji = FakeTmux(window_name="main"), FakeTmux(window_name="main")
        twn.update_tmux_window_name(twn.HookStatus.ONGOING, ID, run=by_status, env=TMUX_ENV)
        twn.update_tmux_window_name(BUSY, ID, run=by_emoji, env=TMUX_ENV)
        self.assertEqual(by_status.renamed_to, f"{ID}{BUSY}main")
        self.assertEqual(by_status.renamed_to, by_emoji.renamed_to)


class TestRemoveTmuxWindowIcon(unittest.TestCase):
    def test_table(self):
        cases = [
            # (説明, env, window_name, fail_on, expected_code, expected_rename)
            ("非tmuxはコード2", {}, "main", (), twn.CLEANUP_NOT_TMUX, None),
            ("名前取得失敗はコード3", TMUX_ENV, "main", {"name"}, twn.CLEANUP_NAME_READ_FAILED, None),
            ("window_id取得失敗はコード4", TMUX_ENV, "main", {"window_id"}, twn.CLEANUP_WINDOW_ID_FAILED, None),
            ("剥がすものなしはコード1", TMUX_ENV, "main", (), twn.CLEANUP_NO_ICON, None),
            ("除去成功はコード0", TMUX_ENV, f"{ID}{BUSY}main", (), twn.CLEANUP_OK, "main"),
            ("バッジも除去", TMUX_ENV, f"{ID}{BUSY}{ALERT}main", (), twn.CLEANUP_OK, "main"),
            ("rename失敗はコード6", TMUX_ENV, f"{ID}{BUSY}main", {"rename"}, twn.CLEANUP_RENAME_FAILED, None),
        ]
        for desc, env, name, fail_on, expected_code, expected_rename in cases:
            with self.subTest(desc):
                fake = FakeTmux(window_name=name, fail_on=fail_on)
                code = twn.remove_tmux_window_icon(run=fake, env=env)
                self.assertEqual(code, expected_code)
                self.assertEqual(fake.renamed_to, expected_rename)

    def test_outside_tmux_spawns_nothing(self):
        fake = FakeTmux()
        twn.remove_tmux_window_icon(run=fake, env={})
        self.assertEqual(fake.calls, [])

    def test_no_icon_skips_rename_call(self):
        fake = FakeTmux(window_name="main")
        twn.remove_tmux_window_icon(run=fake, env=TMUX_ENV)
        self.assertNotIn("rename", fake.calls)

    def test_report_error_prints_legacy_messages(self):
        cases = [
            ("非tmux", {}, "main", (), twn.CLEANUP_NOT_TMUX),
            ("名前取得失敗", TMUX_ENV, "main", {"name"}, twn.CLEANUP_NAME_READ_FAILED),
            ("window_id取得失敗", TMUX_ENV, "main", {"window_id"}, twn.CLEANUP_WINDOW_ID_FAILED),
            ("rename失敗", TMUX_ENV, f"{ID}{BUSY}main", {"rename"}, twn.CLEANUP_RENAME_FAILED),
        ]
        for desc, env, name, fail_on, expected_code in cases:
            with self.subTest(desc):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = twn.remove_tmux_window_icon(
                        report_error=True, run=FakeTmux(window_name=name, fail_on=fail_on), env=env
                    )
                self.assertEqual(code, expected_code)
                self.assertEqual(stderr.getvalue(), twn.CLEANUP_MESSAGES[expected_code] + "\n")

    def test_no_report_by_default(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            twn.remove_tmux_window_icon(run=FakeTmux(), env={})
        self.assertEqual(stderr.getvalue(), "")


class TestContextAlertBadge(unittest.TestCase):
    def test_add_table(self):
        cases = [
            # (説明, window_name, expected_rename)
            ("バッジ追加", f"{ID}{BUSY}main", f"{ID}{BUSY}{ALERT}main"),
            ("プレーン名に追加", "main", f"{ALERT}main"),
            ("既存バッジありはrenameしない", f"{ID}{BUSY}{ALERT}main", None),
        ]
        for desc, name, expected_rename in cases:
            with self.subTest(desc):
                fake = FakeTmux(window_name=name)
                twn.add_context_alert_badge(run=fake, env=TMUX_ENV)
                self.assertEqual(fake.renamed_to, expected_rename)

    def test_remove_table(self):
        cases = [
            # (説明, window_name, expected_code, expected_rename)
            ("バッジだけ外し状態アイコンは残す", f"{ID}{BUSY}{ALERT}main", 0, f"{ID}{BUSY}main"),
            ("バッジ不在は1", f"{ID}{BUSY}main", 1, None),
        ]
        for desc, name, expected_code, expected_rename in cases:
            with self.subTest(desc):
                fake = FakeTmux(window_name=name)
                self.assertEqual(twn.remove_context_alert_badge(run=fake, env=TMUX_ENV), expected_code)
                self.assertEqual(fake.renamed_to, expected_rename)


class TestHookStatusSingleSourceOfTruth(unittest.TestCase):
    def test_values_match_conf(self):
        self.assertEqual(twn.HookStatus.COMPLETED.value, tmux_emoji.EMOJI_STATUS_COMPLETED)
        self.assertEqual(twn.HookStatus.NOTIFICATION.value, tmux_emoji.EMOJI_STATUS_NOTIFICATION)
        self.assertEqual(twn.HookStatus.ONGOING.value, tmux_emoji.EMOJI_STATUS_ONGOING)


class TestCli(unittest.TestCase):
    def test_table(self):
        # tmux外の環境に固定して実tmuxウィンドウへの副作用を防ぐ
        cases = [
            ("removeは非tmuxでコード2", ["remove"], twn.CLEANUP_NOT_TMUX),
            ("updateは非tmuxで0", ["update", WAIT], 0),
            ("update+identifierも0", ["update", WAIT, ID], 0),
            ("update strictも非tmuxで0", ["update", WAIT, "--report-error"], 0),
            ("引数なしはusageエラー", [], twn._EX_USAGE),
            ("不正コマンドはusageエラー", ["bogus"], twn._EX_USAGE),
            ("update引数過多はusageエラー", ["update", WAIT, ID, "extra"], twn._EX_USAGE),
            (
                "report-errorは末尾のみ",
                ["update", "--report-error", WAIT],
                twn._EX_USAGE,
            ),
            ("remove不正フラグはusageエラー", ["remove", "--bogus"], twn._EX_USAGE),
            ("remove-badgeは非tmuxで0", ["remove-badge"], 0),
        ]
        for desc, argv, expected in cases:
            with self.subTest(desc):
                with mock.patch.dict(os.environ, {}, clear=True):
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        self.assertEqual(twn.main(argv), expected)

    def test_update_passes_identifier_through(self):
        cases = [
            # (説明, argv, update_tmux_window_nameへ渡る引数, report_error)
            ("identifier省略は空文字", ["update", WAIT], (WAIT, ""), False),
            ("identifier指定はそのまま", ["update", WAIT, ID], (WAIT, ID), False),
            ("identifier空文字は省略と同じ", ["update", WAIT, ""], (WAIT, ""), False),
            (
                "strictフラグを渡す",
                ["update", WAIT, ID, "--report-error"],
                (WAIT, ID),
                True,
            ),
        ]
        for desc, argv, expected, report_error in cases:
            with self.subTest(desc):
                with mock.patch.object(
                    twn, "update_tmux_window_name", return_value=twn.UPDATE_OK
                ) as fake_update:
                    self.assertEqual(twn.main(argv), 0)
                    fake_update.assert_called_once_with(*expected, report_error=report_error)

    def test_update_strict_propagates_failure_status(self):
        with mock.patch.object(
            twn, "update_tmux_window_name", return_value=twn.UPDATE_RENAME_FAILED
        ) as fake_update:
            code = twn.main(["update", WAIT, ID, "--report-error"])
        self.assertEqual(code, twn.UPDATE_RENAME_FAILED)
        fake_update.assert_called_once_with(WAIT, ID, report_error=True)


class TestShellWrapper(unittest.TestCase):
    def test_update_default_and_strict_table(self):
        cases = [
            # (説明, strict, expected_code, expected_stderr, expected_argv)
            ("既定は失敗を抑制", False, 0, "", ["update", WAIT, ID]),
            (
                "strictは失敗を伝播",
                True,
                6,
                "fake update failure\n",
                ["update", WAIT, ID, "--report-error"],
            ),
        ]
        for desc, strict, expected_code, expected_stderr, expected_argv in cases:
            with self.subTest(desc):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    fake_bin = root / "bin"
                    fake_bin.mkdir()
                    argv_log = root / "argv.log"
                    home_log = root / "home.log"
                    fake_python = fake_bin / "python3"
                    fake_python.write_text(
                        "#!/bin/sh\n"
                        "printf '%s\\n' \"$@\" > \"$TMUX_WRAPPER_ARGV_LOG\"\n"
                        "printf '%s' \"${HOME-}\" > \"$TMUX_WRAPPER_HOME_LOG\"\n"
                        "printf 'fake update failure\\n' >&2\n"
                        "exit 6\n",
                        encoding="utf-8",
                    )
                    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

                    env = os.environ.copy()
                    original_home = env.get("HOME", "")
                    env.update(
                        {
                            "PATH": f"{fake_bin}:{env['PATH']}",
                            "TMUX_PANE": "%1",
                            "TERM_PROGRAM": "tmux",
                            "TMUX_WRAPPER_ARGV_LOG": str(argv_log),
                            "TMUX_WRAPPER_HOME_LOG": str(home_log),
                        }
                    )
                    shell_command = 'source "$1"; update_tmux_window_name "$2" "$3"'
                    command = [
                        "bash",
                        "-c",
                        shell_command + (' "true"' if strict else ""),
                        "wrapper-test",
                        str(REPO_ROOT / "shell" / "tmux" / "tmux_window_name.sh"),
                        WAIT,
                        ID,
                    ]
                    result = subprocess.run(
                        command,
                        cwd=REPO_ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=5,
                    )

                    self.assertEqual(result.returncode, expected_code)
                    self.assertEqual(result.stderr, expected_stderr)
                    argv = argv_log.read_text(encoding="utf-8").splitlines()
                    self.assertEqual(argv[-len(expected_argv) :], expected_argv)
                    self.assertEqual(home_log.read_text(encoding="utf-8"), original_home)


if __name__ == "__main__":
    unittest.main()
