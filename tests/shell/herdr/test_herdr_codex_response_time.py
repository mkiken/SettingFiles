import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.support import sanitized_env


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("response_time", ROOT / "shell/herdr/herdr-codex-response-time.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResponseTimeTest(unittest.TestCase):
    def test_latest_complete_record_and_partial_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "log.jsonl"
            complete = lambda epoch: json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "completed_at": epoch}})
            transcript.write_text(complete(100) + "\n" + json.dumps({"type": "event_msg", "payload": {"type": "task_started"}}) + "\n" + complete(200))
            with patch.object(MODULE, "find_session_transcript_path", return_value=str(transcript)):
                self.assertEqual(MODULE.last_completion("session"), 100)
                with transcript.open("a") as stream:
                    stream.write("\n")
                self.assertEqual(MODULE.last_completion("session"), 200)

    def test_missing_log(self):
        with patch.object(MODULE, "find_session_transcript_path", return_value=None):
            self.assertIsNone(MODULE.last_completion("session"))

    def test_focus_reports_all(self):
        panes = [{"pane_id": "a", "agent": "codex", "agent_session": {"value": "one"}, "tokens": {}},
                 {"pane_id": "b", "agent": "codex", "agent_session": {"value": "two"}, "tokens": {}}]
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if args[1:3] == ["pane", "list"]:
                result = {"panes": panes}
            elif args[1:3] == ["pane", "get"]:
                result = {"pane": next(p for p in panes if p["pane_id"] == args[3])}
            else:
                result = {}
            return type("Result", (), {"stdout": json.dumps({"result": result}).encode()})()
        from io import StringIO
        output = StringIO()
        with patch.object(MODULE.subprocess, "run", side_effect=run), patch.object(MODULE.time, "time", return_value=1192), patch.object(MODULE, "last_completion", return_value=1000), patch.dict(MODULE.os.environ, {"HERDR_PANE_ID": "b"}), patch("sys.stdout", output):
            MODULE.main()
        self.assertEqual(output.getvalue().strip(), "🟢 📩03:12")
        self.assertEqual(sum(args[1:3] == ["pane", "report-metadata"] for args in calls), 2)

    def test_session_change_prevents_report(self):
        pane = {"pane_id": "a", "agent": "codex", "agent_session": {"value": "old"}, "tokens": {}}
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            result = {"panes": [pane]} if args[2] == "list" else {"pane": {**pane, "agent_session": {"value": "new"}}}
            return type("Result", (), {"stdout": json.dumps({"result": result}).encode()})()
        from io import StringIO
        output = StringIO()
        with patch.object(MODULE.subprocess, "run", side_effect=run), patch.object(MODULE.time, "time", return_value=1192), patch.object(MODULE, "last_completion", return_value=1000), patch.dict(MODULE.os.environ, {"HERDR_PANE_ID": "a"}), patch("sys.stdout", output):
            MODULE.main()
        self.assertFalse(any(args[2] == "report-metadata" for args in calls))
        self.assertEqual(output.getvalue().strip(), "")

    def test_fake_cli_and_real_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = root / "sessions"
            sessions.mkdir()
            (sessions / "rollout-test.jsonl").write_text(json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "completed_at": int(time.time()) - 192}}) + "\n")
            fake = root / "herdr"
            calls = root / "calls"
            pane = {"pane_id": "p", "agent": "codex", "agent_session": {"value": "test"}, "tokens": {}}
            fake.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$TEST_CALLS\"\ncase \"$2\" in\nlist) printf '%s' \"$TEST_LIST\";;\nget) printf '%s' \"$TEST_GET\";;\nesac\n")
            fake.chmod(0o755)
            env = sanitized_env(CODEX_HOME=str(root), HERDR_BIN_PATH=str(fake), HERDR_PANE_ID="p", TEST_CALLS=str(calls), TEST_LIST=json.dumps({"result": {"panes": [pane]}}), TEST_GET=json.dumps({"result": {"pane": pane}}))
            result = subprocess.run([sys.executable, str(SPEC.origin)], env=env, capture_output=True, text=True, check=True)
            self.assertIn(result.stdout.strip(), ("🟢 📩03:12", "🟢 📩03:13"))
            self.assertIn("codex_last_response=📩", calls.read_text())

    def test_color_boundaries_and_hours(self):
        pane = {"pane_id": "a", "agent": "codex", "agent_session": {"value": "one"}, "tokens": {}}
        def run(args, **kwargs):
            result = {"panes": [pane]} if args[2] == "list" else {"pane": pane}
            return type("Result", (), {"stdout": json.dumps({"result": result}).encode()})()
        from io import StringIO
        for elapsed, expected in [(1499, "🟢 24:59"), (1500, "🟡 25:00"), (1799, "🟡 29:59"), (1800, "🔴 30:00"), (3600, "🔴 1:00:00")]:
            with self.subTest(elapsed=elapsed):
                output = StringIO()
                with patch.object(MODULE.subprocess, "run", side_effect=run), patch.object(MODULE.time, "time", return_value=1000 + elapsed), patch.object(MODULE, "last_completion", return_value=1000), patch.dict(MODULE.os.environ, {"HERDR_PANE_ID": "a"}), patch("sys.stdout", output):
                    MODULE.main()
                color, duration = expected.split()
                self.assertEqual(output.getvalue().strip(), f"{color} 📩{duration}")


if __name__ == "__main__":
    unittest.main()
