"""shell/tmux/herdr_status_icon.sh の単体テスト。

実herdr CLIには依存せず、fake_bin/herdrで tab get/tab rename/tab list/
workspace report-metadata の呼び出しを記録し、状態アイコンの付与・除去・
識別子継承・workspaceのOR集約を検証する。
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "shell/tmux/herdr_status_icon.sh"


def marker_relpath(tab_id: str) -> Path:
    """シェル✋マーカーのXDG_CACHE_HOME相対パス（スクリプトのキー式を再現）。"""
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", tab_id)
    return Path("herdr-shell-status") / "default" / sanitized

# tmux_emoji.conf の実値（テストでも実物を使う。理由はtest_herdr_plugin_notify.py
# のコメント通り: strip系ロジックはUnicode絵文字専用パターンなのでASCIIスタブでは
# 検証できない）。
DONE = "✅"
ERROR = "❌"
WAIT = "✋"
BUSY = "🤖"
ID_CLAUDE = "✴️"


class HerdrStatusIconTestBase(unittest.TestCase):
    def run_shell(
        self,
        function_call: str,
        *,
        pane_id: str = "w1:p1",
        tab_id: str = "w1:t1",
        workspace_id: str = "w1",
        tab_label: str = "main",
        tab_list_labels: list[str] | None = None,
        herdr_present: bool = True,
        herdr_env: bool = True,
        tmux_env: bool = False,
        notify_silent: bool = False,
        marker_content: str | None = None,
        marker_age_seconds: int = 0,
        extra_env: dict | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], list[str], list[str], str | None]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            rename_calls = root / "rename_calls"
            metadata_calls = root / "metadata_calls"
            cache_dir = root / "cache"
            marker_file = cache_dir / marker_relpath(tab_id)
            if marker_content is not None:
                marker_file.parent.mkdir(parents=True, exist_ok=True)
                marker_file.write_text(marker_content + "\n", encoding="utf-8")
                if marker_age_seconds:
                    past = marker_file.stat().st_mtime - marker_age_seconds
                    os.utime(marker_file, (past, past))

            tab_result = {"result": {"tab": {"label": tab_label, "tab_id": tab_id}}}
            pane_result = {
                "result": {"pane": {"tab_id": tab_id, "workspace_id": workspace_id}}
            }
            labels = tab_list_labels if tab_list_labels is not None else [tab_label]
            tab_list_result = {
                "result": {
                    "tabs": [
                        {"tab_id": f"w1:t{i}", "label": label}
                        for i, label in enumerate(labels)
                    ]
                }
            }

            if herdr_present:
                fake_herdr = fake_bin / "herdr"
                fake_herdr.write_text(
                    "#!/bin/bash\n"
                    'if [[ "$1" == "tab" && "$2" == "get" ]]; then\n'
                    f"  echo '{json.dumps(tab_result)}'\n"
                    'elif [[ "$1" == "tab" && "$2" == "rename" ]]; then\n'
                    '  echo "$3|$4" >> "$HERDR_TEST_RENAME_CALLS"\n'
                    'elif [[ "$1" == "tab" && "$2" == "list" ]]; then\n'
                    f"  echo '{json.dumps(tab_list_result)}'\n"
                    'elif [[ "$1" == "pane" && "$2" == "get" ]]; then\n'
                    f"  echo '{json.dumps(pane_result)}'\n"
                    'elif [[ "$1" == "workspace" && "$2" == "report-metadata" ]]; then\n'
                    '  echo "$*" >> "$HERDR_TEST_METADATA_CALLS"\n'
                    "fi\n",
                    encoding="utf-8",
                )
                fake_herdr.chmod(0o755)

            env = os.environ.copy()
            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            real_python3 = shutil.which("python3")
            self.assertIsNotNone(real_python3)
            # python3のdirnameを最優先にする: /usr/bin/jq経由でdirname(jq)=/usr/binが
            # 混ざると、型ヒント(str | None)未対応の古いシステムPython3.9が先に解決され
            # tmux_window_name.pyの起動時にSyntaxError相当で落ちてしまうため。
            path_entries = [
                str(fake_bin),
                os.path.dirname(real_python3),
                os.path.dirname(real_jq),
                "/usr/bin:/bin",
            ]
            env.update(
                {
                    "HERDR_TEST_RENAME_CALLS": str(rename_calls),
                    "HERDR_TEST_METADATA_CALLS": str(metadata_calls),
                    "PATH": ":".join(path_entries),
                }
            )
            # tmux/herdr判定用の環境変数はテストごとに完全制御するため既存値を落とす
            for key in ("TMUX", "TERM_PROGRAM", "HERDR_ENV", "HERDR_PANE_ID", "HERDR_TAB_ID", "HERDR_WORKSPACE_ID", "NOTIFY_SILENT", "HERDR_SOCKET_PATH"):
                env.pop(key, None)
            # マーカーが実環境の ~/.cache に漏れない/から漏れ込まないよう必ず隔離する
            env["XDG_CACHE_HOME"] = str(cache_dir)
            if tmux_env:
                env["TMUX"] = "/tmp/tmux-1000/default,1,0"
            if herdr_env:
                env["HERDR_ENV"] = "1"
                env["HERDR_PANE_ID"] = pane_id
                env["HERDR_TAB_ID"] = tab_id
                env["HERDR_WORKSPACE_ID"] = workspace_id
            if notify_silent:
                env["NOTIFY_SILENT"] = "1"
            if extra_env:
                env.update(extra_env)

            command = (
                f'source "{SCRIPT}"\n'
                f"{function_call}\n"
            )
            result = subprocess.run(
                ["bash", "-c", command],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            rename = rename_calls.read_text(encoding="utf-8").splitlines() if rename_calls.exists() else []
            metadata = metadata_calls.read_text(encoding="utf-8").splitlines() if metadata_calls.exists() else []
            marker_after = (
                marker_file.read_text(encoding="utf-8").strip()
                if marker_file.exists()
                else None
            )
            return result, rename, metadata, marker_after


class UpdateHerdrStatusIconTest(HerdrStatusIconTestBase):
    def test_plain_label_gets_status_icon(self):
        result, rename, _, _ = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"', tab_label="main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [f"w1:t1|{WAIT}main"])

    def test_identifier_is_preserved_across_status_change(self):
        result, rename, _, _ = self.run_shell(
            f'update_herdr_status_icon "{DONE}"', tab_label=f"{ID_CLAUDE}{BUSY}Claude Code"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [f"w1:t1|{ID_CLAUDE}{DONE}Claude Code"])

    def test_jump_index_is_preserved_across_status_change(self):
        result, rename, _, _ = self.run_shell(
            f'update_herdr_status_icon "{DONE}"',
            tab_label=f"[2] {ID_CLAUDE}{BUSY}Claude Code",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [f"w1:t1|[2] {ID_CLAUDE}{DONE}Claude Code"])

    def test_idempotent_when_label_already_matches(self):
        result, rename, _, _ = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"', tab_label=f"{WAIT}main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [])

    def test_no_op_outside_herdr(self):
        result, rename, metadata, _ = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"', herdr_env=False, tab_label="main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [])
        self.assertEqual(metadata, [])

    def test_no_op_inside_tmux(self):
        # tmux/Herdrは排他。TMUXがセットされていればHerdr側は何もしない。
        result, rename, metadata, _ = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"', tmux_env=True, tab_label="main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [])
        self.assertEqual(metadata, [])

    def test_no_op_when_notify_silent(self):
        result, rename, metadata, _ = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"', notify_silent=True, tab_label="main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [])
        self.assertEqual(metadata, [])

    def test_workspace_metadata_reports_aggregated_icon(self):
        result, _, metadata, _ = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"',
            tab_label="main",
            tab_list_labels=[f"{WAIT}main"],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any("shell_status=" + WAIT in line for line in metadata), metadata)

    def test_workspace_aggregates_across_multiple_tabs_by_priority(self):
        # 優先度 WAIT > ERROR > BUSY > DONE。BUSYとDONEが混在してもWAITが勝つ。
        result, _, metadata, _ = self.run_shell(
            f'update_herdr_status_icon "{DONE}"',
            tab_label=f"{BUSY}other",
            tab_list_labels=[f"{BUSY}other", f"{WAIT}main2", f"{DONE}main3"],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any("shell_status=" + WAIT in line for line in metadata), metadata)


class ShellStatusMarkerTest(HerdrStatusIconTestBase):
    """シェル所有✋マーカー（プラグインのラベル再構築から✋を守る所有権シグナル）。"""

    def test_wait_update_writes_marker(self):
        result, _, _, marker = self.run_shell(
            f'update_herdr_status_icon "{WAIT}"', tab_label="main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(marker, WAIT)

    def test_non_wait_update_removes_marker(self):
        # ✅/❌での更新は入力待ちの終了を意味し、既存マーカーを消す
        for emoji in (DONE, ERROR):
            with self.subTest(emoji=emoji):
                result, _, _, marker = self.run_shell(
                    f'update_herdr_status_icon "{emoji}"',
                    tab_label=f"{WAIT}main",
                    marker_content=WAIT,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsNone(marker)

    def test_remove_deletes_marker(self):
        result, _, _, marker = self.run_shell(
            "remove_herdr_status_icon",
            tab_label=f"{WAIT}main",
            marker_content=WAIT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(marker)

    def test_no_marker_written_when_unavailable(self):
        # Herdr外/tmux内/NOTIFY_SILENTでは_herdr_status_availableが弾くので書かない
        for kwargs in (
            {"herdr_env": False},
            {"tmux_env": True},
            {"notify_silent": True},
        ):
            with self.subTest(**kwargs):
                result, _, _, marker = self.run_shell(
                    f'update_herdr_status_icon "{WAIT}"', tab_label="main", **kwargs
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsNone(marker)

    def test_marker_read_validity_boundaries(self):
        # (前提マーカー内容, mtimeの過去シフト秒, 期待stdout, 期待残存) の表駆動。
        # TTL=86400秒ちょうどは境界のレース（now取得までの経過秒）があるため±60秒で判定
        cases = [
            ("fresh", WAIT, 0, WAIT, WAIT),
            ("near_ttl", WAIT, 86400 - 60, WAIT, WAIT),
            ("stale", WAIT, 86400 + 60, "", None),
            ("garbage", "not-an-emoji", 0, "", None),
        ]
        for name, content, age, expected_stdout, expected_marker in cases:
            with self.subTest(case=name):
                result, _, _, marker = self.run_shell(
                    '_herdr_shell_status_marker_read "w1:t1"',
                    marker_content=content,
                    marker_age_seconds=age,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected_stdout)
                self.assertEqual(marker, expected_marker)

    def test_marker_read_missing_file_is_empty(self):
        result, _, _, marker = self.run_shell('_herdr_shell_status_marker_read "w1:t1"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")
        self.assertIsNone(marker)


class RemoveHerdrStatusIconTest(HerdrStatusIconTestBase):
    def test_removes_status_icon_but_keeps_identifier(self):
        result, rename, _, _ = self.run_shell(
            "remove_herdr_status_icon", tab_label=f"{ID_CLAUDE}{DONE}Claude Code"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [f"w1:t1|{ID_CLAUDE}Claude Code"])

    def test_remove_keeps_jump_index_and_identifier(self):
        result, rename, _, _ = self.run_shell(
            "remove_herdr_status_icon",
            tab_label=f"[2] {ID_CLAUDE}{DONE}Claude Code",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [f"w1:t1|[2] {ID_CLAUDE}Claude Code"])

    def test_idempotent_when_no_icon_present(self):
        result, rename, _, _ = self.run_shell("remove_herdr_status_icon", tab_label="main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [])

    def test_clears_workspace_token_when_no_tab_has_status(self):
        result, _, metadata, _ = self.run_shell(
            "remove_herdr_status_icon",
            tab_label=f"{WAIT}main",
            tab_list_labels=["main"],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any("--clear-token" in line and "shell_status" in line for line in metadata), metadata)

    def test_no_op_outside_herdr(self):
        result, rename, metadata, _ = self.run_shell(
            "remove_herdr_status_icon", herdr_env=False, tab_label=f"{DONE}main"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rename, [])
        self.assertEqual(metadata, [])


if __name__ == "__main__":
    unittest.main()
