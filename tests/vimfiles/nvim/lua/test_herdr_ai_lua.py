import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import sanitized_env

ROOT = Path(__file__).resolve().parents[4]
NVIM_DIR = ROOT / "vimfiles/nvim"

SELF_PANE = "wX3:p1"
SELF_TAB = "wX3:t1"

# キー列を実キーマップ経由で流し、通知は呼び出し側から読めるようファイルへ書き出す。
DRIVER = """
vim.g.mapleader = " "
local notes = {}
vim.notify = function(msg) table.insert(notes, msg) end
local pick = tonumber(os.getenv("TEST_PICK") or "")
if pick then
  vim.ui.select = function(items, _, cb) cb(items[pick]) end
end
require("herdr_ai")
vim.cmd("edit " .. vim.fn.fnameescape(os.getenv("TEST_FILE")))
local keys = vim.api.nvim_replace_termcodes(os.getenv("TEST_KEYS"), true, false, true)
vim.api.nvim_feedkeys(keys, "x", false)
vim.fn.writefile(notes, os.getenv("TEST_NOTES"))
vim.cmd("qa!")
"""

STUB = """#!/bin/sh
if [ "$1 $2" = "pane list" ]; then cat "$STUB_DIR/list.json"; exit 0; fi
if [ "$1 $2" = "pane send-text" ]; then printf '%s|%s\\n' "$3" "$4" >> "$STUB_DIR/sent.log"; exit 0; fi
printf '%s\\n' "$*" >> "$STUB_DIR/unexpected.log"
exit 1
"""

TRAP = """#!/bin/sh
echo invoked >> "$TRAP_LOG"
exit 1
"""


def pane(pane_id, tab_id, agent, cwd):
    return {"pane_id": pane_id, "tab_id": tab_id, "agent": agent, "cwd": cwd}


@unittest.skipUnless(shutil.which("nvim"), "nvim is required")
class HerdrAiTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.project = self.tmp / "proj"
        (self.project / "sub").mkdir(parents=True)
        self.target = self.project / "sub/file.lua"
        self.target.write_text("".join(f"line {i}\n" for i in range(1, 31)))
        self.stub_dir = self.tmp / "stub"
        self.stub_dir.mkdir()
        stub = self.stub_dir / "herdr"
        stub.write_text(STUB)
        stub.chmod(0o755)
        self.driver = self.tmp / "driver.lua"
        self.driver.write_text(DRIVER)
        # PATH 上の herdr は罠。HERDR_BIN_PATH のスタブが優先されれば一度も呼ばれない。
        self.trap_dir = self.tmp / "trapbin"
        self.trap_dir.mkdir()
        trap = self.trap_dir / "herdr"
        trap.write_text(TRAP)
        trap.chmod(0o755)
        self.trap_log = self.tmp / "trap.log"
        self.notes = self.tmp / "notes.txt"

    def run_nvim(self, panes, keys, pane_id=SELF_PANE, pick=None):
        (self.stub_dir / "list.json").write_text(json.dumps({"result": {"panes": panes}}))
        overrides = {
            "HERDR_BIN_PATH": str(self.stub_dir / "herdr"),
            "STUB_DIR": str(self.stub_dir),
            "TRAP_LOG": str(self.trap_log),
            "TEST_FILE": str(self.target),
            "TEST_KEYS": keys,
            "TEST_NOTES": str(self.notes),
            "PATH": f"{self.trap_dir}:/usr/bin:/bin:{Path(shutil.which('nvim')).parent}",
        }
        if pane_id:
            overrides["HERDR_PANE_ID"] = pane_id
        if pick:
            overrides["TEST_PICK"] = str(pick)
        result = subprocess.run(
            ["nvim", "--headless", "-u", "NONE", "--cmd", f"set rtp^={NVIM_DIR}", "-c", f"luafile {self.driver}"],
            env=sanitized_env(overrides),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.trap_log.exists(), "PATH 上の herdr が呼ばれた")
        self.assertFalse((self.stub_dir / "unexpected.log").exists())

    def sent(self):
        log = self.stub_dir / "sent.log"
        return log.read_text().splitlines() if log.exists() else []

    def notices(self):
        return self.notes.read_text().splitlines()

    def claude_pane(self, cwd=None, pane_id="wX3:p2"):
        return pane(pane_id, SELF_TAB, "claude", cwd or str(self.project))

    def test_normal_mode_sends_relative_path_with_current_line(self):
        panes = [pane(SELF_PANE, SELF_TAB, None, str(self.project)), self.claude_pane()]
        self.run_nvim(panes, "12G<Space>at")
        self.assertEqual(self.sent(), ["wX3:p2|sub/file.lua:12 "])

    def test_visual_mode_sends_line_range(self):
        self.run_nvim([self.claude_pane()] + [pane(SELF_PANE, SELF_TAB, None, "/x")], "12GV8j<Space>at")
        self.assertEqual(self.sent(), ["wX3:p2|sub/file.lua:12-20 "])

    def test_visual_mode_backward_selection_is_ordered(self):
        self.run_nvim([self.claude_pane(), pane(SELF_PANE, SELF_TAB, None, "/x")], "20GV8k<Space>at")
        self.assertEqual(self.sent(), ["wX3:p2|sub/file.lua:12-20 "])

    def test_send_file_omits_line_spec(self):
        self.run_nvim([self.claude_pane(), pane(SELF_PANE, SELF_TAB, None, "/x")], "5G<Space>af")
        self.assertEqual(self.sent(), ["wX3:p2|sub/file.lua "])

    def test_file_outside_pane_cwd_uses_absolute_path(self):
        panes = [self.claude_pane(cwd=str(self.tmp / "elsewhere")), pane(SELF_PANE, SELF_TAB, None, "/x")]
        self.run_nvim(panes, "3G<Space>at")
        self.assertEqual(self.sent(), [f"wX3:p2|{self.target}:3 "])

    def test_ignores_other_tab_agent_and_non_agent_pane_in_same_tab(self):
        panes = [
            pane(SELF_PANE, SELF_TAB, None, "/x"),
            pane("wX9:p1", "wX9:t1", "claude", str(self.project)),
            pane("wX3:p3", SELF_TAB, None, str(self.project)),
        ]
        self.run_nvim(panes, "12G<Space>at")
        self.assertEqual(self.sent(), [])
        self.assertTrue(any("AI ペイン" in n for n in self.notices()), self.notices())

    def test_outside_herdr_does_not_send(self):
        self.run_nvim([self.claude_pane()], "12G<Space>at", pane_id=None)
        self.assertEqual(self.sent(), [])
        self.assertTrue(any("HERDR_PANE_ID" in n for n in self.notices()), self.notices())

    def test_multiple_ai_panes_sends_to_selected_one(self):
        panes = [
            pane(SELF_PANE, SELF_TAB, None, "/x"),
            self.claude_pane(),
            pane("wX3:p3", SELF_TAB, "codex", str(self.project)),
        ]
        self.run_nvim(panes, "12G<Space>at", pick=2)
        self.assertEqual(self.sent(), ["wX3:p3|sub/file.lua:12 "])


if __name__ == "__main__":
    unittest.main()
