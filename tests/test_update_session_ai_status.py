"""shell/tmux/update-session-ai-status.sh の単体テスト。

session内の全windowを✋>❌>🤖>✅の優先度でOR集約し、@session_ai_status
user optionに書き込む。fake tmux binでlist-windows/set-optionの呼び出しを
記録し、優先度・境界値（全idle→unset）を検証する。
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "shell/tmux/update-session-ai-status.sh"

WAIT = "✋"
ERROR = "❌"
BUSY = "🤖"
DONE = "✅"
ALERT = "⚠️"


class UpdateSessionAiStatusTest(unittest.TestCase):
    def run_script(self, window_names: list[str], session_id: str = "1") -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            set_option_calls = root / "set_option_calls"

            windows_output = "\n".join(window_names)
            fake_tmux = fake_bin / "tmux"
            fake_tmux.write_text(
                "#!/bin/bash\n"
                'if [[ "$1" == "list-windows" ]]; then\n'
                f'  printf \'%s\\n\' "{windows_output}"\n'
                'elif [[ "$1" == "set-option" ]]; then\n'
                '  echo "$*" >> "$SET_OPTION_CALLS"\n'
                "fi\n",
                encoding="utf-8",
            )
            fake_tmux.chmod(0o755)

            import os
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:/usr/bin:/bin"
            env["SET_OPTION_CALLS"] = str(set_option_calls)

            result = subprocess.run(
                ["bash", str(SCRIPT), session_id],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            calls = set_option_calls.read_text(encoding="utf-8").splitlines() if set_option_calls.exists() else []
            return result, calls

    def test_priority_table(self):
        cases = [
            # (説明, window_names, expected_icon_in_set_option)
            ("waitが最優先", [f"{WAIT}a", f"{BUSY}b", f"{DONE}c"], WAIT),
            ("errorはbusy/doneより優先", [f"{ERROR}a", f"{BUSY}b", f"{DONE}c"], ERROR),
            ("waitはerrorより優先", [f"{WAIT}a", f"{ERROR}b"], WAIT),
            ("busyはdoneより優先", [f"{BUSY}a", f"{DONE}b"], BUSY),
            ("doneのみ", [f"{DONE}a"], DONE),
            ("errorのみ", [f"{ERROR}a"], ERROR),
        ]
        for desc, window_names, expected_icon in cases:
            with self.subTest(desc):
                result, calls = self.run_script(window_names)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(
                    any(expected_icon in line for line in calls),
                    calls,
                )
                # unset(-qu)は呼ばれない
                self.assertFalse(any("-qu" in line for line in calls), calls)

    def test_no_status_icons_unsets_option(self):
        result, calls = self.run_script(["main", "other"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any("-qu" in line for line in calls), calls)

    def test_context_badge_is_appended(self):
        result, calls = self.run_script([f"{BUSY}a{ALERT}"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(BUSY in line and ALERT in line for line in calls), calls)

    def test_missing_session_id_is_no_op(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), ""], cwd=REPO_ROOT, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
