import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HOOK = REPO_ROOT / "ai" / "codex" / "hooks" / "codex-hook.py"


class CodexHookTest(unittest.TestCase):
    def run_hook(self, hook_input: str):
        with tempfile.TemporaryDirectory() as tmp_dir:
            error_log = Path(tmp_dir) / "codex-hook-error.log"
            env = os.environ.copy()
            env["CODEX_HOOK_ERROR_LOG"] = str(error_log)
            result = subprocess.run(
                [sys.executable, str(HOOK)],
                input=hook_input,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            log_text = error_log.read_text(encoding="utf-8") if error_log.exists() else ""
            return result, log_text, error_log

    def assert_visible_hook_error(
        self,
        result: subprocess.CompletedProcess,
        log_text: str,
        error_log: Path,
        expected_reason: str,
    ):
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(expected_reason, result.stderr)
        self.assertIn(f"Hook error log: {error_log}", result.stderr)
        self.assertNotIn("/path/to", result.stderr)
        self.assertNotIn("To inspect it", result.stderr)
        self.assertIn(expected_reason, log_text)

    def test_empty_stdin_exits_with_visible_log_path(self):
        result, log_text, error_log = self.run_hook("")

        self.assert_visible_hook_error(result, log_text, error_log, "empty hook stdin")

    def test_invalid_json_exits_with_visible_log_path(self):
        result, log_text, error_log = self.run_hook("{")

        self.assert_visible_hook_error(result, log_text, error_log, "invalid hook input JSON")
        self.assertIn("input_bytes=1", log_text)


if __name__ == "__main__":
    unittest.main()
