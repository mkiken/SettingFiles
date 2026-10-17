"""Herdr workspace close picker: listing, confirmation and close ordering."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


SCRIPT = REPO_ROOT / "shell/herdr/herdr-workspace-close-picker.sh"

WORKSPACES = [
    {"workspace_id": "w1", "label": "[1] alpha", "active_tab_id": "w1:t1", "focused": True},
    {"workspace_id": "w2", "label": "[2] beta", "active_tab_id": "w2:t1", "focused": False},
    {"workspace_id": "w3", "label": "[3] gamma", "active_tab_id": "w3:t1", "focused": False},
]


class HerdrWorkspaceClosePickerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.log = self.root / "calls"
        self.fake = self.root / "fake-herdr"
        self.fake.write_text(
            "#!/bin/bash\n"
            "printf '%s\\n' \"$*\" >> \"$TEST_CALLS\"\n"
            "case \"$1 $2\" in\n"
            "  'workspace list') printf '%s\\n' \"$TEST_WORKSPACES\" ;;\n"
            "  'pane list') printf '{\"result\":{\"panes\":[]}}\\n' ;;\n"
            "  'workspace close') [[ \" ${TEST_CLOSE_FAIL:-} \" == *\" $3 \"* ]] && exit 1; exit 0 ;;\n"
            "  *) exit 9 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        self.fake.chmod(0o755)
        # TEST_FZF_PICK の id を指定順に出力する fzf。TEST_FZF_RC が非 0 なら何も選ばず終了する。
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fzf = self.bin / "fzf"
        fzf.write_text(
            "#!/bin/bash\n"
            "rows=$(cat)\n"
            "[[ ${TEST_FZF_RC:-0} != 0 ]] && exit \"$TEST_FZF_RC\"\n"
            "for id in $TEST_FZF_PICK; do grep -F -- \"$id\"$'\\t' <<< \"$rows\"; done\n",
            encoding="utf-8",
        )
        fzf.chmod(0o755)
        # PATH 上の herdr が呼ばれたら痕跡を残す罠。HERDR_BIN_PATH の stub だけが使われることを確かめる。
        trap_bin = self.root / "trap-bin"
        trap_bin.mkdir()
        self.trap_log = self.root / "trap-called"
        trap = trap_bin / "herdr"
        trap.write_text(f"#!/bin/bash\ntouch '{self.trap_log}'\nexit 1\n", encoding="utf-8")
        trap.chmod(0o755)
        self.trap_bin = trap_bin
        self.home = self.root / "home"
        self.home.mkdir()

    def run_script(self, *args, stdin="", workspaces=WORKSPACES, **env_extra):
        env = sanitized_env({
            "HERDR_BIN_PATH": str(self.fake),
            "HOME": str(self.home),
            "PATH": f"{self.trap_bin}:{self.bin}:/usr/bin:/bin",
            "TEST_CALLS": str(self.log),
            "TEST_WORKSPACES": json.dumps({"result": {"workspaces": workspaces}}),
            **env_extra,
        })
        result = subprocess.run(
            [str(SCRIPT), *args], input=stdin, capture_output=True, text=True, env=env,
        )
        self.assertFalse(self.trap_log.exists(), "herdr on PATH must not be invoked")
        return result

    def close_calls(self):
        if not self.log.exists():
            return []
        return [line for line in self.log.read_text().splitlines()
                if line.startswith("workspace close")]

    def test_list_puts_focused_workspace_last(self):
        result = self.run_script("--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [line.split("\t")[0] for line in result.stdout.splitlines()], ["w2", "w3", "w1"])
        self.assertIn("* [1] alpha", result.stdout.splitlines()[-1])

    def test_selected_workspaces_close_in_list_order_with_current_last(self):
        result = self.run_script(stdin="y", TEST_FZF_PICK="w1 w3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.close_calls(), ["workspace close w3", "workspace close w1"])

    def test_declined_confirmation_closes_nothing(self):
        for answer in ("n", "", "\n"):
            with self.subTest(answer=answer):
                result = self.run_script(stdin=answer, TEST_FZF_PICK="w2")
                self.assertEqual(result.returncode, 130)
                self.assertEqual(self.close_calls(), [])

    def test_fzf_cancel_closes_nothing(self):
        result = self.run_script(stdin="y", TEST_FZF_RC="130")
        self.assertEqual(result.returncode, 130)
        self.assertEqual(self.close_calls(), [])

    def test_no_workspaces_fails_loudly(self):
        result = self.run_script(stdin="y", workspaces=[], TEST_FZF_PICK="w1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no herdr workspaces", result.stderr)
        self.assertEqual(self.close_calls(), [])

    def test_close_failure_continues_and_exits_nonzero(self):
        result = self.run_script(stdin="y", TEST_FZF_PICK="w2 w3", TEST_CLOSE_FAIL="w2")
        self.assertEqual(result.returncode, 1)
        self.assertIn("failed to close w2", result.stderr)
        self.assertEqual(self.close_calls(), ["workspace close w2", "workspace close w3"])


if __name__ == "__main__":
    unittest.main()
