import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

HOOK = REPO_ROOT / "ai/gemini/hooks/gemini-hook.py"

# 呼び出し引数をログへ記録し、tab getには固定ラベルを返すherdrスタブ。
STUB = """#!/bin/bash
echo "$*" >> "$HERDR_TEST_LOG"
if [[ "$1 $2" == "tab get" ]]; then
  echo "{\\"result\\":{\\"tab\\":{\\"label\\":\\"$HERDR_TEST_LABEL\\"}}}"
fi
"""


class GeminiHookHerdrTabIconTest(unittest.TestCase):
    """Geminiはnotify-richから外れているため、Herdr下ではhookがタブ名へ直接アイコンを書く。"""

    def run_hook(self, event, *, label, in_herdr=True):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stub = root / "herdr"
            stub.write_text(STUB, encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            log = root / "log"
            env = sanitized_env(
                {
                    "HERDR_BIN_PATH": str(stub),
                    "HERDR_TAB_ID": "w1:t2",
                    "HERDR_TEST_LOG": str(log),
                    "HERDR_TEST_LABEL": label,
                    "TMUX_PANE": "",
                    "TERM_PROGRAM": "",
                }
            )
            if in_herdr:
                env["HERDR_ENV"] = "1"
            else:
                env.pop("HERDR_ENV", None)
            subprocess.run(
                ["python3", "-I", str(HOOK), event],
                env=env,
                input=json.dumps({}),
                text=True,
                capture_output=True,
                check=True,
            )
            return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def test_before_tool_sets_ongoing_icon_under_herdr(self):
        for event in ("before_agent", "before_tool", "after_tool"):
            with self.subTest(event=event):
                calls = self.run_hook(event, label="[2] w1")
                self.assertEqual(calls[-1], "tab rename w1:t2 [2] 💎🤖w1")

    def test_session_end_strips_status_but_keeps_identifier_under_herdr(self):
        calls = self.run_hook("session_end", label="💎✅w1")
        self.assertEqual(calls[-1], "tab rename w1:t2 💎w1")

    def test_outside_herdr_never_calls_herdr(self):
        # tmux外・Herdr外ではどのCLIも叩かない（herdrスタブの呼び出しログが空）。
        self.assertEqual(self.run_hook("before_tool", label="w1", in_herdr=False), [])


if __name__ == "__main__":
    unittest.main()
