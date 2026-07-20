import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "shell" / "tmux" / "tmux-file-picker.sh"


def run_fn(fn_and_args: str, env_extra: dict | None = None, path_prepend: str | None = None) -> subprocess.CompletedProcess:
    # tmux-file-picker.sh は冒頭で `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"` するため、
    # fake コマンドを効かせるには source の後で再度 PATH 先頭に差し込む必要がある。
    script = f'source "{SCRIPT}"; '
    if path_prepend:
        script += f'export PATH="{path_prepend}:$PATH"; '
    script += fn_and_args
    env = {**os.environ}
    # Multiplexer 検出に使う環境変数はテスト間で漏れないよう毎回明示的にリセットする。
    env.pop("TMUX", None)
    env.pop("HERDR_ENV", None)
    env.pop("HERDR_ACTIVE_PANE_ID", None)
    env.pop("HERDR_ACTIVE_PANE_CWD", None)
    env.pop("HERDR_BIN_PATH", None)
    env.update(env_extra or {})
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)


def write_fake_bin(directory: str, name: str, body: str) -> None:
    path = Path(directory) / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class MuxDetectTest(unittest.TestCase):
    def test_tmux_env_set_detects_tmux(self):
        result = run_fn("_mux_detect", {"TMUX": "/tmp/tmux-1000/default,1234,0"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "tmux")

    def test_herdr_env_set_detects_herdr(self):
        result = run_fn("_mux_detect", {"HERDR_ENV": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "herdr")

    def test_neither_set_detects_none(self):
        result = run_fn("_mux_detect")
        self.assertEqual(result.stdout.strip(), "none")

    def test_both_set_prefers_tmux(self):
        # tmux セッション内で HERDR_ENV が漏れ継承していても既存の tmux フローを変えない。
        result = run_fn(
            "_mux_detect",
            {"TMUX": "/tmp/tmux-1000/default,1234,0", "HERDR_ENV": "1"},
        )
        self.assertEqual(result.stdout.strip(), "tmux")


class AiAtPathTest(unittest.TestCase):
    def test_prefixes_path_with_at(self):
        result = run_fn('_ai_at_path "src/main.ts"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "@src/main.ts")


class MuxPaneIdHerdrTest(unittest.TestCase):
    def test_returns_active_pane_id(self):
        result = run_fn('_mux_pane_id herdr', {"HERDR_ACTIVE_PANE_ID": "w1:pE"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "w1:pE")

    def test_missing_active_pane_id_errors(self):
        result = run_fn('_mux_pane_id herdr')
        self.assertNotEqual(result.returncode, 0)


class MuxPaneDirHerdrTest(unittest.TestCase):
    def test_returns_active_pane_cwd(self):
        result = run_fn(
            '_mux_pane_dir herdr w1:pE',
            {"HERDR_ACTIVE_PANE_CWD": "/Users/example/repo"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "/Users/example/repo")

    def test_missing_active_pane_cwd_errors(self):
        result = run_fn('_mux_pane_dir herdr w1:pE')
        self.assertNotEqual(result.returncode, 0)


@unittest.skipUnless(shutil.which("jq"), "jq required")
class MuxIsAiPaneHerdrTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.bin_dir = self._tmp.name

    def _fake_herdr(self, agent_json_field: str) -> None:
        write_fake_bin(
            self.bin_dir,
            "herdr",
            f'echo \'{{"result":{{"pane":{{"agent":{agent_json_field}}}}}}}\'',
        )

    def test_claude_agent_detected(self):
        self._fake_herdr('"claude"')
        result = run_fn(
            "_mux_is_ai_pane herdr w1:pE",
            path_prepend=self.bin_dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_gemini_agent_detected(self):
        self._fake_herdr('"gemini"')
        result = run_fn("_mux_is_ai_pane herdr w1:pE", path_prepend=self.bin_dir)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_agent_returns_false(self):
        self._fake_herdr("null")
        result = run_fn("_mux_is_ai_pane herdr w1:pE", path_prepend=self.bin_dir)
        self.assertNotEqual(result.returncode, 0)

    def test_unrelated_agent_name_returns_false(self):
        self._fake_herdr('"some-other-tool"')
        result = run_fn("_mux_is_ai_pane herdr w1:pE", path_prepend=self.bin_dir)
        self.assertNotEqual(result.returncode, 0)

    def test_herdr_command_failure_returns_false_not_error(self):
        # herdr CLI 呼び出し失敗（pipefail）でスクリプトが即終了しないことを確認
        write_fake_bin(self.bin_dir, "herdr", "exit 1")
        result = run_fn("_mux_is_ai_pane herdr w1:pE", path_prepend=self.bin_dir)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")


class MuxSendTextTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.bin_dir = self._tmp.name
        self.record_file = Path(self.bin_dir) / "recorded_args"

    def test_herdr_send_text_passes_two_args_only(self):
        # `herdr pane send-text` は <pane_id> <text> の2引数固定で `--` セパレータを解釈しない
        # （実機検証で `--` を挟むと text 先頭に "--" がリテラル混入する不具合を確認済み）。
        write_fake_bin(
            self.bin_dir,
            "herdr",
            f'printf "%s\\n" "$@" > "{self.record_file}"',
        )
        result = run_fn(
            '_mux_send_text herdr w1:pE "@src/main.ts @README.md "',
            path_prepend=self.bin_dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = self.record_file.read_text().splitlines()
        self.assertEqual(recorded, ["pane", "send-text", "w1:pE", "@src/main.ts @README.md "])

    def test_tmux_send_text_calls_send_keys(self):
        write_fake_bin(
            self.bin_dir,
            "tmux",
            f'printf "%s\\n" "$@" > "{self.record_file}"',
        )
        result = run_fn(
            '_mux_send_text tmux %1 "@src/main.ts "',
            path_prepend=self.bin_dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = self.record_file.read_text().splitlines()
        self.assertEqual(recorded, ["send-keys", "-t", "%1", "@src/main.ts "])


if __name__ == "__main__":
    unittest.main()
