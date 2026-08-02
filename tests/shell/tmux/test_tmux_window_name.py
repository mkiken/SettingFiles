"""shell/tmux/tmux_window_name.py の単体テスト（FakeTmuxランナー注入、実tmux不要）"""
import contextlib
import io
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from support import REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "shell" / "tmux"))

import tmux_emoji
import tmux_window_name as twn

ID = tmux_emoji.EMOJI_ID_CLAUDE  # ✴️
ID_GEMINI = tmux_emoji.EMOJI_ID_GEMINI  # 💎
ID_CODEX = tmux_emoji.EMOJI_ID_CODEX  # 🪷
DONE = tmux_emoji.EMOJI_STATUS_COMPLETED  # ✅
ERROR = tmux_emoji.EMOJI_STATUS_ERROR  # ❌
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


class TestSplitIdentifierPrefix(unittest.TestCase):
    def test_table(self):
        cases = [
            # (説明, name, expected_identifier, expected_rest)
            ("Claude識別子を検出", f"{ID}main", ID, "main"),
            ("Gemini識別子を検出", f"{ID_GEMINI}main", ID_GEMINI, "main"),
            ("Codex識別子を検出", f"{ID_CODEX}main", ID_CODEX, "main"),
            ("識別子+状態アイコン", f"{ID}{BUSY}main", ID, f"{BUSY}main"),
            ("識別子なし", "main", "", "main"),
            ("状態アイコンのみ(識別子ではない)", f"{BUSY}main", "", f"{BUSY}main"),
            ("空文字境界", "", "", ""),
        ]
        for desc, name, expected_identifier, expected_rest in cases:
            with self.subTest(desc):
                self.assertEqual(
                    tmux_emoji.split_identifier_prefix(name),
                    (expected_identifier, expected_rest),
                )


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

    def test_identifier_omitted_inherits_from_current_label(self):
        # シェル状態フック（AI以外）はAI識別子を知らずに呼ぶ。identifier省略時は
        # 現ラベル先頭のAI識別子(✴️/💎/🪷)を継承し、状態アイコンだけ後勝ちで
        # 差し替える（AIアイコンをシェル状態の更新で消してしまわないため）。
        cases = [
            # (説明, current, status_emoji, expected)
            ("Claude識別子を継承", f"{ID}{BUSY}main", DONE, f"{ID}{DONE}main"),
            ("Codex識別子を継承", f"{ID_CODEX}{BUSY}main", DONE, f"{ID_CODEX}{DONE}main"),
            ("識別子なしはそのまま", "main", DONE, f"{DONE}main"),
            ("バッジも保持したまま継承", f"{ID}{BUSY}{ALERT}main", DONE, f"{ID}{DONE}{ALERT}main"),
        ]
        for desc, current, status_emoji, expected in cases:
            with self.subTest(desc):
                fake = FakeTmux(window_name=current)
                twn.update_tmux_window_name(status_emoji, run=fake, env=TMUX_ENV)
                self.assertEqual(fake.renamed_to, expected)

    def test_explicit_identifier_still_overrides_current_label(self):
        # AIフックは常にidentifierを明示的に渡す（partial(..., identifier=IDENTIFIER)）。
        # 明示指定時は継承ロジックを迂回し、これまで通り指定値がそのまま使われる。
        fake = FakeTmux(window_name=f"{ID}{BUSY}main")
        twn.update_tmux_window_name(DONE, ID_CODEX, run=fake, env=TMUX_ENV)
        self.assertEqual(fake.renamed_to, f"{ID_CODEX}{DONE}main")


class TestComputeUpdatedLabel(unittest.TestCase):
    """tmuxに触らずラベル文字列だけを計算する純粋関数（Herdr側シェルスクリプトが
    tmuxに依存せず同じロジックを再利用するために使う）。"""

    def test_table(self):
        cases = [
            # (説明, current, status_emoji, identifier, expected)
            ("識別子を継承(update_tmux_window_nameと同じ挙動)", f"{ID}{BUSY}main", DONE, None, f"{ID}{DONE}main"),
            ("識別子なしはそのまま", "main", DONE, None, f"{DONE}main"),
            ("明示identifierは現ラベルの識別子を上書き", f"{ID}{BUSY}main", DONE, ID_CODEX, f"{ID_CODEX}{DONE}main"),
            ("明示空文字identifierは識別子を消す", f"{ID}{BUSY}main", DONE, "", f"{DONE}main"),
            ("バッジ保持", f"{ID}{BUSY}{ALERT}main", DONE, None, f"{ID}{DONE}{ALERT}main"),
            ("Herdr番号prefix保持", f"[2] {ID}{BUSY}main", DONE, None, f"[2] {ID}{DONE}main"),
            ("二桁は番号prefix扱いしない", f"[10] {ID}{BUSY}main", DONE, None, f"{DONE}[10] {ID}{BUSY}main"),
        ]
        for desc, current, status_emoji, identifier, expected in cases:
            with self.subTest(desc):
                self.assertEqual(
                    twn.compute_updated_label(current, status_emoji, identifier),
                    expected,
                )


class TestComputeRebasedLabel(unittest.TestCase):
    """Herdrタブ本文だけをworktree概要へ置き換える純粋関数。"""

    def test_table(self):
        cases = [
            ("番号・識別子・状態保持", f"[4] {ID_CODEX}{BUSY}4", "worktree-tab-name", f"[4] {ID_CODEX}{BUSY}worktree-tab-name"),
            ("Claude識別子・完了状態保持", f"[2] {ID}{DONE}old", "new-worktree", f"[2] {ID}{DONE}new-worktree"),
            ("context badge保持", f"{ID}{WAIT}{ALERT}old", "new", f"{ID}{WAIT}{ALERT}new"),
            ("prefixなし", "old", "new", "new"),
            ("20文字は省略しない", f"{ID}{BUSY}old", "12345678901234567890", f"{ID}{BUSY}12345678901234567890"),
            ("21文字は末尾ellipsis", f"{ID}{BUSY}old", "123456789012345678901", f"{ID}{BUSY}1234567890123456789…"),
        ]
        for desc, current, base_label, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.compute_rebased_label(current, base_label), expected)


class TestComputeCleanedLabel(unittest.TestCase):
    """状態アイコンだけを除去し、AI識別子は残すラベル計算（tmuxのcontextバッジ除去と
    同様、Herdr側で「状態だけ外す」ために使う）。"""

    def test_table(self):
        cases = [
            # (説明, current, expected)
            ("識別子は残し状態のみ除去", f"{ID}{DONE}main", f"{ID}main"),
            ("識別子なしは状態除去のみ", f"{WAIT}main", "main"),
            ("バッジは保持", f"{ID}{DONE}{ALERT}main", f"{ID}{ALERT}main"),
            ("状態アイコンなしは不変", f"{ID}main", f"{ID}main"),
            ("Herdr番号prefix保持", f"[9] {ID}{DONE}main", f"[9] {ID}main"),
        ]
        for desc, current, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.compute_cleaned_label(current), expected)


class TestIsHerdrDefaultLabel(unittest.TestCase):
    """Herdrが自動採番/自動命名しただけのラベル（連番数字 or 既知agent自動命名名）かを
    判定する純粋関数。Trueなら会話概要への差し替え対象、Falseならユーザー手動命名として温存する。"""

    def test_table(self):
        cases = [
            # (説明, base_label, expected)
            ("連番数字1桁", "1", True),
            ("連番数字複数桁", "42", True),
            ("Claude自動命名", "Claude Code", True),
            ("Codex自動命名", "Codex", True),
            ("Gemini自動命名", "Gemini", True),
            ("ユーザー手動命名は温存", "My Task", False),
            ("差し替え後の会話概要は再判定でも温存(冪等性の要)", "Claude Code タブ名の動作確認", False),
            ("数字を含むが純数字でない", "tab1", False),
            ("空文字境界", "", False),
            ("大文字小文字違いは非一致(厳密一致)", "claude code", False),
            ("部分一致は非該当", "Claude Code Extra", False),
            ("絶対パス完全形は弾く", "/Users/a13596/Desktop/repository/SettingFiles", True),
            ("絶対パス先頭20文字切れ形を弾く(実バグ再現)", "/Users/a13596/Deskt", True),
            ("ルート単体", "/", True),
            ("ホーム~始まりを弾く", "~/Desktop/repo", True),
            ("~単体", "~", True),
            ("$HOME前方一致", os.path.expanduser("~"), True),
            ("スラッシュ含む正当な概要(スペース有)は温存", "feat/xxx を実装", False),
            ("相対パス風概要(スペース有)は温存", "src/foo.ts を修正", False),
            ("単なるファイル名は温存", "foo.ts", False),
            ("スラッシュ+スペースの概要は温存", "a/b の修正", False),
            ("スペース含む絶対パス風は概要優先で温存(弱点の明文化)", "/tmp foo", False),
        ]
        for desc, base_label, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.is_herdr_default_label(base_label), expected)


class TestIsEditorSetTitle(unittest.TestCase):
    """外部エディタ($EDITOR)がOSC 2で設定したファイル名由来のタイトルかを判定する
    純粋関数。Trueなら会話概要とみなさずタブ名・通知本文に採用しない。
    is_herdr_default_label（上書きしてよいラベルか）とは別の問いなので統合しない。"""

    def test_table(self):
        cases = [
            # (説明, title, expected)
            # --- True: エディタ由来（実測形式が最優先） ---
            (
                "実測値そのもの: nvimのsuffix付き実タイトル(バグの直接エンコード)",
                "claude-prompt-93285509-1acc-4720-81fa-d5abaa99870a.md"
                " (/private/tmp/claude-501) - Nvim",
                True,
            ),
            (
                "変更済みバッファ形式(nvim titlestring仕様の + 付き)",
                "claude-prompt-x.md + (/private/tmp/claude-501) - Nvim",
                True,
            ),
            (
                "filename単体(suffixなし境界)",
                "claude-prompt-a0a9e2b3-d3ad-43c4-9760-963e3f11c1c8.md",
                True,
            ),
            ("パス付きfilename(第1トークンのbasenameで捕捉)", "/private/tmp/claude-501/claude-prompt-x.md", True),
            # 実フローではゲートはtruncate前の完全なtitle_textに対して走るため
            # これがゲート入力になることはない。前方一致規則が拡張子に依存しない
            # ことの性質テストとして保持する。
            ("拡張子が落ちた形(前方一致は拡張子非依存)", "claude-prompt-a0a9e2", True),
            (
                "実測値そのもの: COMMIT_EDITMSGのsuffix付き実タイトル"
                "(第1トークン抽出なしではVCSルールがデッドコードになる)",
                "COMMIT_EDITMSG (~/Desktop/repository/SettingFiles/.git) - Nvim",
                True,
            ),
            ("COMMIT_EDITMSG単体", "COMMIT_EDITMSG", True),
            ("MERGE_MSG単体", "MERGE_MSG", True),
            ("git-rebase-todo単体", "git-rebase-todo", True),
            # --- False: 正当な会話概要の温存（スラッグ概要を守ることが最重要） ---
            ("実在のスペース無しスラッグ概要", "mdts-plan-single-file-review", False),
            ("実在のスペース無しスラッグ概要(20字切れ形)", "herdr-pane-copy-shel", False),
            (
                "実測の正当概要: claude-promptを文中に含むが第1トークンはFix",
                "Fix neovim tab naming in claude-prompt editing",
                False,
            ),
            # 拡張子リスト方式なら誤爆したケース。同方式を採らなかった判断の固定。
            ("スラッグ概要+md拡張子", "update-readme.md", False),
            ("スラッグ概要+py拡張子", "fix-tmux-window-name.py", False),
            ("スラッグ概要+lua拡張子", "refactor-options.lua", False),
            ("ファイル名で始まる日本語概要", "api.ts の型を修正", False),
            ("スラッシュ含む概要", "feat/x を実装", False),
            ("ファイル名+日本語の概要", "README.md を更新", False),
            ("日本語概要", "AI レビューフローの改善方法を相談", False),
            ("空文字境界(クラッシュしないこと)", "", False),
            ("空白のみ境界", "   ", False),
            # Herdrデフォルトラベルの除外はis_herdr_default_labelの責務。
            # 2述語で責務を重複させないことの保証。
            ("既知agent自動命名名はここではFalse", "Claude Code", False),
            ("ハイフン無しの前方一致境界(弾かない)", "claude-prompt", False),
            ("採用済みの良いラベル再投入(冪等性の要)", "PR review サブエージェント機能", False),
        ]
        for desc, title, expected in cases:
            with self.subTest(desc):
                self.assertEqual(twn.is_editor_set_title(title), expected)


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
            # identifier省略/空文字は None を渡し、現ラベルからの継承に委ねる
            # （シェル状態フックはAI識別子を知らずに呼ぶため）。
            ("identifier省略はNone(継承)", ["update", WAIT], (WAIT, None), False),
            ("identifier指定はそのまま", ["update", WAIT, ID], (WAIT, ID), False),
            ("identifier空文字はNoneと同じ(継承)", ["update", WAIT, ""], (WAIT, None), False),
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


class TestComputeLabelCli(unittest.TestCase):
    """Herdr側シェルスクリプトが tmux に触らずラベル計算だけをCLI経由で使うための
    サブコマンド。tmux外環境でも常に動作する（pane_id判定を経由しないため）。
    """

    def test_compute_updated_label_table(self):
        cases = [
            # (説明, argv, expected_stdout)
            ("識別子継承", ["compute-updated-label", f"{ID}{BUSY}main", DONE], f"{ID}{DONE}main"),
            ("識別子なし", ["compute-updated-label", "main", DONE], f"{DONE}main"),
            (
                "明示identifierで上書き",
                ["compute-updated-label", f"{ID}{BUSY}main", DONE, ID_CODEX],
                f"{ID_CODEX}{DONE}main",
            ),
            (
                "明示空文字identifierで消す",
                ["compute-updated-label", f"{ID}{BUSY}main", DONE, ""],
                f"{DONE}main",
            ),
            (
                "Herdr番号prefix保持",
                ["compute-updated-label", f"[2] {ID}{BUSY}main", DONE],
                f"[2] {ID}{DONE}main",
            ),
        ]
        for desc, argv, expected_stdout in cases:
            with self.subTest(desc):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = twn.main(argv)
                self.assertEqual(code, 0)
                self.assertEqual(stdout.getvalue(), expected_stdout + "\n")

    def test_compute_cleaned_label_table(self):
        cases = [
            # (説明, argv, expected_stdout)
            ("識別子は残し状態のみ除去", ["compute-cleaned-label", f"{ID}{DONE}main"], f"{ID}main"),
            ("識別子なしは状態除去のみ", ["compute-cleaned-label", f"{WAIT}main"], "main"),
            ("Herdr番号prefix保持", ["compute-cleaned-label", f"[2] {ID}{DONE}main"], f"[2] {ID}main"),
        ]
        for desc, argv, expected_stdout in cases:
            with self.subTest(desc):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = twn.main(argv)
                self.assertEqual(code, 0)
                self.assertEqual(stdout.getvalue(), expected_stdout + "\n")

    def test_compute_rebased_label_preserves_prefixes_and_truncates(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = twn.main(
                [
                    "compute-rebased-label",
                    f"[4] {ID_CODEX}{BUSY}4",
                    "worktree-task-plan-handoff",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(
            stdout.getvalue(),
            f"[4] {ID_CODEX}{BUSY}worktree-task-plan-…\n",
        )

    def test_compute_updated_label_missing_args_is_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = twn.main(["compute-updated-label", "main"])
        self.assertEqual(code, twn._EX_USAGE)

    def test_compute_cleaned_label_missing_args_is_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = twn.main(["compute-cleaned-label"])
        self.assertEqual(code, twn._EX_USAGE)

    def test_compute_rebased_label_missing_args_is_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = twn.main(["compute-rebased-label", "main"])
        self.assertEqual(code, twn._EX_USAGE)

    def test_is_herdr_default_label_table(self):
        # 呼び出し側（zsh）が終了コードだけを見て分岐できるよう、
        # 該当=0（真）/非該当=1（偽）をそのまま終了コードとして返す。
        cases = [
            # (説明, argv, expected_code)
            ("連番数字は該当(0)", ["is-herdr-default-label", "1"], 0),
            ("既知agent名は該当(0)", ["is-herdr-default-label", "Claude Code"], 0),
            ("手動命名は非該当(1)", ["is-herdr-default-label", "My Task"], 1),
            ("フルパス切れ形は該当(0)", ["is-herdr-default-label", "/Users/a13596/Deskt"], 0),
            ("ホーム~始まりは該当(0)", ["is-herdr-default-label", "~/repo"], 0),
            ("正当な会話概要は非該当(1)", ["is-herdr-default-label", "feat/x を実装"], 1),
        ]
        for desc, argv, expected_code in cases:
            with self.subTest(desc):
                self.assertEqual(twn.main(argv), expected_code)

    def test_is_herdr_default_label_missing_args_is_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = twn.main(["is-herdr-default-label"])
        self.assertEqual(code, twn._EX_USAGE)

    def test_is_editor_set_title_table(self):
        # is-herdr-default-labelと同じ規約: 該当=0（真）/非該当=1（偽）。
        # 呼び出し側(zsh)は0/1以外を「判定不能」としてfail-closedに倒す。
        cases = [
            # (説明, argv, expected_code)
            (
                "nvim実測タイトルは該当(0)",
                [
                    "is-editor-set-title",
                    "claude-prompt-x.md (/private/tmp/claude-501) - Nvim",
                ],
                0,
            ),
            (
                "VCS実測タイトルは該当(0)",
                ["is-editor-set-title", "COMMIT_EDITMSG (~/repo/.git) - Nvim"],
                0,
            ),
            (
                "スラッグ概要は非該当(1)",
                ["is-editor-set-title", "mdts-plan-single-file-review"],
                1,
            ),
            (
                "拡張子付きスラッグ概要は非該当(1)",
                ["is-editor-set-title", "update-readme.md"],
                1,
            ),
        ]
        for desc, argv, expected_code in cases:
            with self.subTest(desc):
                self.assertEqual(twn.main(argv), expected_code)

    def test_is_editor_set_title_missing_args_is_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = twn.main(["is-editor-set-title"])
        self.assertEqual(code, twn._EX_USAGE)

    def test_analyze_herdr_label_table(self):
        cases = [
            (
                "既定ラベルと通常概要",
                f"{ID}{DONE}Claude Code",
                "日本語の概要",
                {
                    "BASE_LABEL": "Claude Code",
                    "BASE_IS_DEFAULT": "1",
                    "TITLE_IS_DEFAULT": "0",
                    "EDITOR_TITLE_RC": "1",
                },
            ),
            (
                "引用符・改行を含む手動ラベルとエディタtitle",
                f"{ID}{WAIT}日本語 '引用\n改行",
                "claude-prompt-x.md (/private/tmp) - Nvim",
                {
                    "BASE_LABEL": "日本語 '引用\n改行",
                    "BASE_IS_DEFAULT": "0",
                    "TITLE_IS_DEFAULT": "0",
                    "EDITOR_TITLE_RC": "0",
                },
            ),
            (
                "Herdr既定title",
                "manual",
                "Claude Code",
                {
                    "BASE_LABEL": "manual",
                    "BASE_IS_DEFAULT": "0",
                    "TITLE_IS_DEFAULT": "1",
                    "EDITOR_TITLE_RC": "1",
                },
            ),
        ]
        for description, label, title, expected in cases:
            with self.subTest(description=description):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = twn.main(["analyze-herdr-label", label, title])
                assignments = dict(
                    token.split("=", 1) for token in shlex.split(stdout.getvalue())
                )
                self.assertEqual(code, 0)
                self.assertEqual(assignments, expected)

    def test_analyze_herdr_label_requires_exactly_two_arguments(self):
        cases = (
            ["analyze-herdr-label"],
            ["analyze-herdr-label", "label"],
            ["analyze-herdr-label", "label", "title", "extra"],
        )
        for argv in cases:
            with self.subTest(argv=argv):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = twn.main(argv)
                self.assertEqual(code, twn._EX_USAGE)


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
