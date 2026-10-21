import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

SCRIPT = REPO_ROOT / "shell/tmux/tmux_window_name.sh"


class UpdateHerdrTabIconTest(unittest.TestCase):
    def run_fn(self, *, herdr_env):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            log = root / "log"
            # python3スタブ: 実際のherdr/tmuxを叩かず、渡された引数だけ記録する
            stub = bin_dir / "python3"
            stub.write_text('#!/bin/bash\necho "$@" >> "$TEST_LOG"\n', encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            env = sanitized_env({"PATH": f"{bin_dir}:/usr/bin:/bin", "TEST_LOG": str(log)})
            if herdr_env:
                env["HERDR_ENV"] = "1"
            else:
                env.pop("HERDR_ENV", None)
            subprocess.run(
                ["bash", "-c", f'source "{SCRIPT}"; update_herdr_tab_icon "✋" "💎"'],
                env=env,
                check=True,
            )
            return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def test_under_herdr_calls_herdr_update_subcommand(self):
        calls = self.run_fn(herdr_env=True)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith("tmux_window_name.py herdr-update ✋ 💎"), calls)

    def test_outside_herdr_does_not_start_python(self):
        self.assertEqual(self.run_fn(herdr_env=False), [])


if __name__ == "__main__":
    unittest.main()
