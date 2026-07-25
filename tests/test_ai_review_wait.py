import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_review_wait.sh"


class AiReviewWaitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = Path(self.tmp.name)

    def run_wait(self, *files, interval="0.05", timeout="1"):
        env = dict(
            os.environ,
            AI_REVIEW_WAIT_INTERVAL=interval,
            AI_REVIEW_WAIT_TIMEOUT=timeout,
        )
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir), *files],
            env=env, capture_output=True, text=True,
        )

    def test_returns_zero_when_all_present(self):
        (self.run_dir / "claude.md").write_text("result")
        (self.run_dir / "codex.md").write_text("result")
        result = self.run_wait("claude.md", "codex.md")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_file_does_not_count_as_done(self):
        (self.run_dir / "claude.md").write_text("")
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)

    def test_times_out_when_file_missing(self):
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("タイムアウト", result.stderr)

    def test_detects_file_created_during_wait(self):
        def create_later():
            time.sleep(0.3)
            (self.run_dir / "claude.md").write_text("result")

        thread = threading.Thread(target=create_later)
        thread.start()
        result = self.run_wait("claude.md", timeout="5")
        thread.join()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_usage_error_without_files(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
