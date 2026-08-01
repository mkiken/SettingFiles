import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STATUSLINE = REPO_ROOT / "ai/claude/statusline-command.sh"


class ClaudeUsagebarStatuslineTest(unittest.TestCase):
    def run_statusline(
        self,
        payload: dict,
        *,
        usagebar: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["SET"] = str(home / "missing-settingfiles")
            if usagebar is not None:
                target = home / ".claude" / "herdr-agent-usage-statusline.sh"
                target.parent.mkdir()
                target.symlink_to(usagebar)

            return subprocess.run(
                ["/bin/bash", str(STATUSLINE)],
                cwd=REPO_ROOT,
                env=env,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

    def test_forwards_statusline_json_without_changing_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture = Path(tmp) / "input.json"
            usagebar = Path(tmp) / "run-statusline.sh"
            usagebar.write_text(
                "#!/bin/bash\ncat > \"$USAGEBAR_CAPTURE\"\n",
                encoding="utf-8",
            )
            usagebar.chmod(0o755)
            payload = {"model": {"display_name": "Claude"}}

            previous_capture = os.environ.get("USAGEBAR_CAPTURE")
            os.environ["USAGEBAR_CAPTURE"] = str(capture)
            try:
                result = self.run_statusline(payload, usagebar=str(usagebar))
            finally:
                if previous_capture is None:
                    os.environ.pop("USAGEBAR_CAPTURE", None)
                else:
                    os.environ["USAGEBAR_CAPTURE"] = previous_capture

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(capture.read_text(encoding="utf-8")), payload)
            self.assertIn("🤖 Claude", result.stdout)

    def test_missing_usagebar_link_keeps_existing_statusline_available(self):
        result = self.run_statusline({"model": {"display_name": "Claude"}})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("🤖 Claude", result.stdout)

    def test_usagebar_failure_does_not_break_existing_statusline(self):
        with tempfile.TemporaryDirectory() as tmp:
            usagebar = Path(tmp) / "run-statusline.sh"
            usagebar.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
            usagebar.chmod(0o755)

            result = self.run_statusline(
                {"model": {"display_name": "Claude"}}, usagebar=str(usagebar)
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("🤖 Claude", result.stdout)


if __name__ == "__main__":
    unittest.main()
