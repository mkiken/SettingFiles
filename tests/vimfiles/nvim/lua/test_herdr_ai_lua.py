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
local error_seen = false
vim.notify = function(msg, level)
  table.insert(notes, msg)
  if level == vim.log.levels.ERROR then error_seen = true end
end
-- 実 vim.ui.select は headless で入力待ちになるため常に差し替える。既定はキャンセル。
vim.ui.select = function(items, _, cb)
  vim.fn.writefile({ vim.json.encode(items) }, os.getenv("TEST_ITEMS"))
  local pick_value = os.getenv("TEST_PICK_VALUE")
  if pick_value then
    for _, item in ipairs(items) do
      if item == pick_value then return cb(item) end
    end
    return cb(nil)
  end
  cb(items[tonumber(os.getenv("TEST_PICK") or "")])
end
require("herdr_ai")
vim.cmd("edit " .. vim.fn.fnameescape(os.getenv("TEST_FILE")))
local keys = vim.api.nvim_replace_termcodes(os.getenv("TEST_KEYS"), true, false, true)
vim.api.nvim_feedkeys(keys, "x", false)
-- 起動フローは非同期なので、送信の着地かエラー通知まで待つ。
local wait = os.getenv("TEST_WAIT")
if wait == "sent" then
  vim.wait(20000, function() return vim.uv.fs_stat(os.getenv("STUB_DIR") .. "/sent.log") ~= nil end, 50)
elseif wait == "error" then
  vim.wait(20000, function() return error_seen end, 50)
end
vim.fn.writefile(notes, os.getenv("TEST_NOTES"))
vim.cmd("qa!")
"""

STUB = """#!/bin/sh
case "$1 $2" in
  "pane list") cat "$STUB_DIR/list.json"; exit 0 ;;
  "pane send-text") printf '%s|%s\\n' "$3" "$4" >> "$STUB_DIR/sent.log"; exit 0 ;;
  "pane split")
    printf '%s\\n' "$*" >> "$STUB_DIR/launch.log"
    printf '{"result":{"pane":{"pane_id":"wX3:p9"}}}'
    exit 0 ;;
  "pane run"|"pane wait-output"|"pane send-keys")
    printf '%s\\n' "$*" >> "$STUB_DIR/launch.log"
    exit 0 ;;
  "agent wait")
    printf '%s\\n' "$*" >> "$STUB_DIR/launch.log"
    exit "${AGENT_WAIT_EXIT:-0}" ;;
esac
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
        self.items = self.tmp / "items.json"
        # 実 herdr が PATH から見えないよう、必要なツールだけをリンクした dir を PATH に使う。
        self.tools_dir = self.tmp / "tools"
        self.tools_dir.mkdir()
        for tool in ("nvim", "jq"):
            found = shutil.which(tool)
            if found:
                (self.tools_dir / tool).symlink_to(found)

    def run_nvim(self, panes, keys, pane_id=SELF_PANE, pick=None, pick_value=None, wait=None, agent_wait_exit=0):
        (self.stub_dir / "list.json").write_text(json.dumps({"result": {"panes": panes}}))
        overrides = {
            "HERDR_BIN_PATH": str(self.stub_dir / "herdr"),
            "STUB_DIR": str(self.stub_dir),
            "TRAP_LOG": str(self.trap_log),
            "TEST_FILE": str(self.target),
            "TEST_KEYS": keys,
            "TEST_NOTES": str(self.notes),
            "TEST_ITEMS": str(self.items),
            "AGENT_WAIT_EXIT": str(agent_wait_exit),
            # 起動スクリプトは SET 配下から解決される。worktree のものを使わせる。
            "SET": str(ROOT),
            # 起動スクリプトは PATH 上の herdr を使う。スタブを先頭、罠をその次に置く。
            "PATH": f"{self.stub_dir}:{self.trap_dir}:{self.tools_dir}:/usr/bin:/bin",
        }
        if pane_id:
            overrides["HERDR_PANE_ID"] = pane_id
        if pick:
            overrides["TEST_PICK"] = str(pick)
        if pick_value:
            overrides["TEST_PICK_VALUE"] = pick_value
        if wait:
            overrides["TEST_WAIT"] = wait
        result = subprocess.run(
            [shutil.which("nvim"), "--headless", "-u", "NONE", "--cmd", f"set rtp^={NVIM_DIR}", "-c", f"luafile {self.driver}"],
            env=sanitized_env(overrides),
            cwd=self.project,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.trap_log.exists(), "スタブより後ろの PATH 上の herdr が呼ばれた")
        self.assertFalse((self.stub_dir / "unexpected.log").exists())

    def launch_calls(self):
        log = self.stub_dir / "launch.log"
        return log.read_text().splitlines() if log.exists() else []

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

    def test_no_ai_pane_in_tab_cancelled_selection_neither_launches_nor_sends(self):
        # 別タブの AI ペインと、同タブの非 AI ペインだけでは「AI ペイン無し」と扱う。
        panes = [
            pane(SELF_PANE, SELF_TAB, None, "/x"),
            pane("wX9:p1", "wX9:t1", "claude", str(self.project)),
            pane("wX3:p3", SELF_TAB, None, str(self.project)),
        ]
        self.run_nvim(panes, "12G<Space>at")
        self.assertEqual(self.sent(), [])
        self.assertEqual(self.launch_calls(), [])

    def test_no_ai_pane_offers_alias_list_covering_models_and_effort(self):
        self.run_nvim([pane(SELF_PANE, SELF_TAB, None, "/x")], "12G<Space>at")
        offered = set(json.loads(self.items.read_text()))
        expected = {
            "clo", "cls", "clf", "clh", "cloeh", "clseh", "cleh", "clmx",
            "cxs", "cxa", "cxt", "cxl", "cxeh", "cxteh", "cxmx",
            "gmf", "gmp", "gmmx",
        }
        self.assertEqual(offered, expected)

    def test_no_ai_pane_launches_selected_alias_then_sends_reference_to_new_pane(self):
        self.run_nvim([pane(SELF_PANE, SELF_TAB, None, "/x")], "12G<Space>at", pick_value="cxs", wait="sent")
        calls = self.launch_calls()
        self.assertEqual(
            calls[0], f"pane split --pane {SELF_PANE} --direction right --ratio 0.5 --focus --cwd {self.project}"
        )
        self.assertIn("pane run wX3:p9 cxs", calls)
        self.assertEqual(calls[-1], "agent wait wX3:p9 --until idle --until done --timeout 60000")
        self.assertEqual(self.sent(), ["wX3:p9|sub/file.lua:12 "])

    def test_no_ai_pane_launch_keeps_selection_made_before_the_dialog(self):
        self.run_nvim([pane(SELF_PANE, SELF_TAB, None, "/x")], "12GV8j<Space>at", pick_value="gmf", wait="sent")
        self.assertEqual(self.sent(), ["wX3:p9|sub/file.lua:12-20 "])

    def test_launch_failure_reports_error_and_does_not_send(self):
        self.run_nvim(
            [pane(SELF_PANE, SELF_TAB, None, "/x")], "12G<Space>at", pick_value="cxs", wait="error", agent_wait_exit=1
        )
        self.assertEqual(self.sent(), [])
        self.assertTrue(any("wX3:p9" in n for n in self.notices()), self.notices())

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
