import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from tests.support import sanitized_env


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("agent_timers", ROOT / "shell/herdr/herdr-agent-timers.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def pane_of(pane_id, agent, session, tokens=None):
    return {"pane_id": pane_id, "agent": agent, "agent_session": {"value": session}, "tokens": tokens or {}}


def fake_run(panes, calls, get_override=None):
    def run(args, **kwargs):
        calls.append(args)
        if args[1:3] == ["pane", "list"]:
            result = {"panes": panes}
        elif args[1:3] == ["pane", "get"]:
            found = next(p for p in panes if p["pane_id"] == args[3])
            result = {"pane": (get_override or {}).get(args[3], found)}
        else:
            result = {}
        return type("Result", (), {"stdout": json.dumps({"result": result}).encode()})()
    return run


def reports(calls):
    return [args for args in calls if args[1:3] == ["pane", "report-metadata"]]


def run_main(panes, claude_at=None, codex_at=None, now=0, get_override=None):
    calls = []
    output = StringIO()
    timers = {
        "claude": (*MODULE.TIMERS["claude"][:1], lambda sid: claude_at, MODULE.format_claude),
        "codex": (*MODULE.TIMERS["codex"][:1], lambda sid: codex_at, MODULE.format_codex),
    }
    with patch.object(MODULE.subprocess, "run", side_effect=fake_run(panes, calls, get_override)), \
            patch.object(MODULE.time, "time", return_value=now), \
            patch.dict(MODULE.TIMERS, timers), \
            patch("sys.stdout", output):
        MODULE.main()
    return calls, output.getvalue()


class LastCompletionTest(unittest.TestCase):
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


class CacheLastRequestTest(unittest.TestCase):
    def read_with_store(self, content, session_id="sid"):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "plugins/store"
            store.mkdir(parents=True)
            if content is not None:
                (store / "cache-tools_claude-code-cache-tools-abc.json").write_text(content)
            with patch.dict(MODULE.os.environ, {"CLAUDE_CONFIG_DIR": directory}):
                return MODULE.cache_last_request(session_id)

    def test_returns_last_at_in_seconds(self):
        store = json.dumps({"cacheTtl.session.sid": {"lastAt": 1793498302515, "model": "m", "contextTokens": 1}})
        self.assertEqual(self.read_with_store(store), 1793498302.515)

    def test_unknown_session(self):
        store = json.dumps({"cacheTtl.session.other": {"lastAt": 1}})
        self.assertIsNone(self.read_with_store(store))

    def test_missing_store_file(self):
        self.assertIsNone(self.read_with_store(None))

    def test_broken_json(self):
        self.assertIsNone(self.read_with_store("{not json"))

    def test_non_numeric_last_at(self):
        for value in ("1", None, True):
            with self.subTest(value=value):
                store = json.dumps({"cacheTtl.session.sid": {"lastAt": value}})
                self.assertIsNone(self.read_with_store(store))

    def test_unexpected_top_level_shape(self):
        self.assertIsNone(self.read_with_store("[]"))


class FormatTest(unittest.TestCase):
    def test_claude_remaining(self):
        for remaining, expected in [(2520, "🟢⏳42m"), (899, "🟡⏳14m"), (600, "🟡⏳10m"), (60, "🟡⏳1m"),
                                    (45, "🔴⏳<1m"), (0, "🔴⏳失効"), (-30, "🔴⏳失効")]:
            with self.subTest(remaining=remaining):
                self.assertEqual(MODULE.format_claude(10000, 10000 - (3600 - remaining)), expected)

    def test_claude_color_boundary(self):
        # 残りがTTLのちょうど25%なら警告色にしない（25%"未満"で黄）。
        self.assertEqual(MODULE.format_claude(1000, 1000 - (3600 - 900)), "🟢⏳15m")
        self.assertEqual(MODULE.format_claude(1000, 1000 - (3600 - 899)), "🟡⏳14m")

    def test_codex_elapsed_colors_and_hours(self):
        for elapsed, expected in [(180, "🟢⏳3m"), (1499, "🟢⏳24m"), (1500, "🟡⏳25m"), (1799, "🟡⏳29m"),
                                  (1800, "🔴⏳30m"), (3900, "🔴⏳1h05m"), (-5, "🟢⏳0m")]:
            with self.subTest(elapsed=elapsed):
                self.assertEqual(MODULE.format_codex(1000 + elapsed, 1000), expected)


class MainTest(unittest.TestCase):
    def test_reports_claude_and_codex_panes(self):
        panes = [pane_of("c", "claude", "cs"), pane_of("x", "codex", "xs"), pane_of("g", "gemini", "gs")]
        calls, output = run_main(panes, claude_at=0, codex_at=0, now=600)
        sent = reports(calls)
        self.assertEqual(len(sent), 2)
        self.assertIn("claude_cache=🟢⏳50m", sent[0])
        self.assertIn("codex_last_response=🟢⏳10m", sent[1])
        self.assertEqual(sent[0][sent[0].index("--ttl-ms") + 1], "180000")
        self.assertEqual(output.strip(), "")

    def test_pane_without_agent_session_is_skipped(self):
        panes = [{"pane_id": "c", "agent": "claude", "tokens": {}}]
        calls, _ = run_main(panes, claude_at=0)
        self.assertEqual(reports(calls), [])

    def test_session_change_prevents_report(self):
        panes = [pane_of("c", "claude", "old")]
        calls, _ = run_main(panes, claude_at=0, get_override={"c": pane_of("c", "claude", "new")})
        self.assertEqual(reports(calls), [])

    def test_no_record_clears_existing_token(self):
        panes = [pane_of("c", "claude", "cs", {"claude_cache": "🟢⏳1m"})]
        calls, _ = run_main(panes, claude_at=None)
        sent = reports(calls)
        self.assertEqual(len(sent), 1)
        self.assertIn("--clear-token", sent[0])
        self.assertIn("claude_cache", sent[0])

    def test_no_record_and_no_token_does_nothing(self):
        calls, _ = run_main([pane_of("c", "claude", "cs")], claude_at=None)
        self.assertEqual(reports(calls), [])
        self.assertFalse(any(args[1:3] == ["pane", "get"] for args in calls))


class EndToEndTest(unittest.TestCase):
    def test_fake_cli_and_real_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = root / "sessions"
            sessions.mkdir()
            (sessions / "rollout-test.jsonl").write_text(json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "completed_at": int(time.time()) - 192}}) + "\n")
            store = root / "plugins/store"
            store.mkdir(parents=True)
            (store / "cache-tools_x.json").write_text(json.dumps({"cacheTtl.session.cs": {"lastAt": int((time.time() - 600) * 1000)}}))
            fake = root / "herdr"
            calls = root / "calls"
            panes = [pane_of("x", "codex", "test"), pane_of("c", "claude", "cs")]
            fake.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$TEST_CALLS\"\ncase \"$2\" in\nlist) printf '%s' \"$TEST_LIST\";;\nget) printf '%s' \"$TEST_GET\";;\nesac\n")
            fake.chmod(0o755)
            # pane getは常にclaudeペインを返すので、codexペインはセッション不一致で書かれない。
            env = sanitized_env(CODEX_HOME=str(root), CLAUDE_CONFIG_DIR=str(root), HERDR_BIN_PATH=str(fake), TEST_CALLS=str(calls),
                                TEST_LIST=json.dumps({"result": {"panes": panes}}), TEST_GET=json.dumps({"result": {"pane": panes[1]}}))
            result = subprocess.run([sys.executable, str(SPEC.origin)], env=env, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), "")
            recorded = calls.read_text()
            self.assertRegex(recorded, r"claude_cache=🟢⏳(49|50)m")
            self.assertNotIn("codex_last_response", recorded)

    def test_unreachable_cli_prints_empty_and_exits_zero(self):
        env = sanitized_env(HERDR_BIN_PATH="/nonexistent/herdr")
        result = subprocess.run([sys.executable, str(SPEC.origin)], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
