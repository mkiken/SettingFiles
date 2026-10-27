import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from unittest.mock import patch

from support import REPO_ROOT, sanitized_env


SCRIPT = REPO_ROOT / "terminal/herdr/plugins/notify-rich/codex-monthly-credit.py"
spec = importlib.util.spec_from_file_location("codex_monthly_credit", SCRIPT)
credit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credit)


class CodexMonthlyCreditTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.scenario = {"percent": 41, "reset": time.time() + 3600, "agent": "codex"}
        self.write_scenario()
        self.write_cli("herdr", '''
import json, os, sys
from pathlib import Path
root = Path(os.environ["FIXTURE_ROOT"])
with (root / "herdr_calls").open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
scenario = json.loads((root / "scenario").read_text())
if sys.argv[1:3] == ["pane", "get"]:
    gets = root / "gets"
    count = int(gets.read_text()) + 1 if gets.exists() else 1
    gets.write_text(str(count))
    if count > 1 and scenario.get("second_get_error"):
        sys.exit(1)
    agent = scenario.get("second_agent", scenario["agent"]) if count > 1 else scenario["agent"]
    context_file = root / "context"
    context = context_file.read_text() if context_file.exists() else "31%"
    print(json.dumps({"result": {"pane": {"agent": agent, "tokens": {"context": context}}}}))
elif sys.argv[1:3] == ["plugin", "list"]:
    print(json.dumps({"result": {"plugins": [{"plugin_id": "usagebar", "enabled": True,
        "plugin_root": str(root), "actions": [{"id": "refresh", "command": [sys.executable, str(root / "bin/refresh")]}]}]}}))
else:
    print("{}")
''')
        self.write_cli("refresh", '''
import json, os, sys, time
from pathlib import Path
root = Path(os.environ["FIXTURE_ROOT"])
scenario = json.loads((root / "scenario").read_text())
(root / "refresh_env").write_text(json.dumps({k: v for k, v in os.environ.items() if k.startswith("HERDR_PLUGIN_") or k == "HERDR_PANE_ID"}))
if scenario.get("refresh_fail"):
    sys.exit(1)
time.sleep(scenario.get("refresh_delay", 0))
(root / "context").write_text(scenario.get("context", "34%"))
''')
        self.write_cli("codex", '''
import json, os, signal, sys, time
from pathlib import Path
root = Path(os.environ["FIXTURE_ROOT"])
scenario = json.loads((root / "scenario").read_text())
with (root / "codex_calls").open("a") as log:
    log.write("start\\n")
(root / "process_group").write_text(json.dumps([os.getpid(), os.getpgrp()]))
child_pid = None
def stopped(signum, frame):
    (root / "stopped").write_text("yes")
    if child_pid:
        os.waitpid(child_pid, 0)
    sys.exit(0)
signal.signal(signal.SIGTERM, stopped)
if scenario.get("child"):
    child_pid = os.fork()
    if child_pid == 0:
        def child_stopped(*args):
            (root / "child_stopped").write_text("yes")
            sys.exit(0)
        signal.signal(signal.SIGTERM, child_stopped)
        (root / "child_ready").write_text("yes")
        time.sleep(30)
        sys.exit(0)
    while not (root / "child_ready").exists():
        time.sleep(.01)
for line in sys.stdin:
    request = json.loads(line)
    with (root / "requests").open("a") as log:
        log.write(json.dumps(request) + "\\n")
    if request["method"] == "initialize":
        print(json.dumps({"id": 1, "result": {}}), flush=True)
    elif request["method"] == "account/rateLimits/read":
        if scenario.get("wait"):
            time.sleep(30)
        time.sleep(scenario.get("delay", 0))
        if scenario.get("malformed"):
            print("{invalid", flush=True)
        elif scenario.get("error"):
            print(json.dumps({"id": 2, "error": {"code": -1}}), flush=True)
        else:
            value = {"remainingPercent": scenario["percent"], "resetsAt": scenario["reset"]}
            if scenario.get("missing"):
                value = None
            print(json.dumps({"id": 2, "result": {"rateLimits": {"individualLimit": value}}}), flush=True)
''')
        self.trap = self.root / "outside-path-herdr"
        self.trap.write_text("#!/bin/sh\n/usr/bin/touch '" + str(self.root / "trap_called") + "'\nexit 1\n")
        self.trap.chmod(0o755)
        with patch.dict(os.environ, {"HERDR_BIN_PATH": str(self.trap), "HERDR_SOCKET_PATH": "/tmp/trap.sock"}):
            self.env = sanitized_env(
                HOME=str(self.root), XDG_CACHE_HOME=str(self.root / "cache"),
                CODEX_HOME=str(self.root / "codex-home"), FIXTURE_ROOT=str(self.root),
                PATH=str(self.bin) + ":/usr/bin:/bin", HERDR_BIN_PATH=str(self.bin / "herdr"),
                HERDR_PANE_ID="w1:p1", HERDR_PLUGIN_EVENT="pane.focused",
                HERDR_PLUGIN_EVENT_JSON=json.dumps({"data": {"agent": "claude"}}),
            )
        self.addCleanup(lambda: self.assertFalse((self.root / "trap_called").exists()))

    def write_cli(self, name, body):
        path = self.bin / name
        path.write_text("#!" + sys.executable + "\n" + body)
        path.chmod(0o755)

    def write_scenario(self, **changes):
        self.scenario.update(changes)
        (self.root / "scenario").write_text(json.dumps(self.scenario))

    def run_hook(self, **changes):
        result = subprocess.run([sys.executable, str(SCRIPT)], env=dict(self.env, **changes),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        return self.reports()[-1]

    def reports(self):
        return [args for args in map(json.loads, (self.root / "herdr_calls").read_text().splitlines())
                if args[:2] == ["pane", "report-metadata"]]

    def fetch_count(self):
        path = self.root / "codex_calls"
        return len(path.read_text().splitlines()) if path.exists() else 0

    def cache_path(self):
        return next((self.root / "cache/herdr-codex-monthly").glob("*.json"))

    def assert_cleared(self, report, codex=True):
        self.assertEqual(report, ["pane", "report-metadata", "w1:p1", "--source",
                                  "codex-monthly-credit", "--clear-token", "context_icon",
                                  "--token" if codex else "--clear-token",
                                  "context_compact=💬34%" if codex else "context_compact",
                                  "--clear-token", "monthly_credit"])

    def test_percent_boundaries_and_protocol(self):
        for value in (41, 0, 100):
            with self.subTest(value=value):
                self.write_scenario(percent=value)
                with patch.object(credit, "TIMEOUT", 2):
                    self.assertEqual(credit.read_credit(self.env)[0], value)
                self.assertTrue((self.root / "stopped").exists())
                pid, group = json.loads((self.root / "process_group").read_text())
                self.assertEqual(pid, group)
                self.assertNotEqual(group, os.getpgrp())
        report = self.run_hook()
        self.assertIn("monthly_credit=📅0%", report)
        self.assertIn("context_compact=💬34%", report)
        self.assertFalse(any(arg.startswith("context=") for arg in report))
        requests = [json.loads(line)["method"] for line in (self.root / "requests").read_text().splitlines()]
        self.assertEqual(requests[:3], ["initialize", "initialized", "account/rateLimits/read"])

    def test_monthly_usage_from_fresh_and_cached_remaining_credit(self):
        for remaining, expected in ((100, "0"), (0, "100"), (41, "59"), (41.5, "58.5")):
            with self.subTest(remaining=remaining):
                self.write_scenario(percent=remaining)
                if self.fetch_count():
                    self.cache_path().write_text("broken")
                before = self.fetch_count()
                for _ in range(2):
                    self.assertIn("monthly_credit=📅{}%".format(expected), self.run_hook())
                self.assertEqual(self.fetch_count(), before + 1)

    def test_invalid_missing_and_api_error_clear_only_owned_token(self):
        scenarios = [{"percent": value} for value in (True, False, -1, 101, "41", None, float("nan"))]
        scenarios += [{"missing": True}, {"error": True}, {"malformed": True}]
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                self.write_scenario(percent=41, missing=False, error=False, malformed=False)
                self.write_scenario(**scenario)
                cache_files = list((self.root / "cache/herdr-codex-monthly").glob("*.json"))
                for path in cache_files:
                    path.write_text("broken")
                self.assert_cleared(self.run_hook())
                self.assertTrue((self.root / "stopped").exists())

    def test_timeout_terminates_launcher_and_child(self):
        self.write_scenario(wait=True, child=True)
        with patch.object(credit, "TIMEOUT", 2):
            self.assertIsNone(credit.cached_credit(self.env))
        self.assertTrue((self.root / "child_ready").exists())
        self.assertTrue((self.root / "stopped").exists())
        for _ in range(50):
            if (self.root / "child_stopped").exists():
                break
            time.sleep(.01)
        self.assertTrue((self.root / "child_stopped").exists())
        self.assert_cleared(self.run_hook())
        self.assertEqual(self.fetch_count(), 1)

    def test_cache_shared_by_panes_and_failure_cached(self):
        self.run_hook()
        self.assertIn("w1:p2", self.run_hook(HERDR_PANE_ID="w1:p2"))
        self.assertEqual(self.fetch_count(), 1)
        stored = json.loads(self.cache_path().read_text())
        self.assertEqual(set(stored), {"fetched_at", "remaining_percent", "resets_at"})
        self.assertEqual(stored["remaining_percent"], 41)
        self.write_scenario(error=True)
        self.cache_path().write_text("broken")
        self.assert_cleared(self.run_hook())
        self.assert_cleared(self.run_hook())
        self.assertEqual(self.fetch_count(), 2)

    def test_expired_corrupt_and_monthly_reset_refresh(self):
        self.run_hook()
        for content in ("broken", "[]", json.dumps({"fetched_at": time.time() - 61,
                            "remaining_percent": 41, "resets_at": time.time() + 3600}),
                        json.dumps({"fetched_at": time.time(), "remaining_percent": 41,
                                    "resets_at": time.time() - 1})):
            with self.subTest(content=content):
                before = self.fetch_count()
                self.cache_path().write_text(content)
                self.run_hook()
                self.assertEqual(self.fetch_count(), before + 1)

    def test_concurrent_events_fetch_once(self):
        self.write_scenario(delay=.2)
        processes = [subprocess.Popen([sys.executable, str(SCRIPT)], env=self.env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual((process.returncode, stdout, stderr), (0, b"", b""))
        self.assertEqual(self.fetch_count(), 1)
        self.assertEqual(len(self.reports()), 3)

    def test_current_agent_wins_over_event_and_clears_non_codex(self):
        self.write_scenario(agent="claude")
        self.assert_cleared(self.run_hook(HERDR_PLUGIN_EVENT_JSON='{"data":{"agent":"codex"}}'), codex=False)
        self.assertEqual(self.fetch_count(), 0)

    def test_pane_changes_agent_during_read(self):
        self.write_scenario(second_agent="claude")
        self.assert_cleared(self.run_hook(), codex=False)
        self.assertEqual(self.fetch_count(), 1)

    def test_event_pane_shapes_and_three_manifest_hooks(self):
        manifest = tomllib.loads((SCRIPT.parent / "herdr-plugin.toml").read_text())
        hooks = [event for event in manifest["events"] if SCRIPT.name in event["command"]]
        self.assertEqual({event["on"] for event in hooks},
                         {"pane.agent_status_changed", "pane.agent_detected", "pane.focused"})
        self.assertEqual(len(hooks), 3)
        for hook, data in zip(hooks, ({"pane_id": "w1:p1"}, {"pane": {"pane_id": "w1:p1"}}, {"pane_id": "w1:p1"})):
            self.assertIn("monthly_credit=📅59%", self.run_hook(
                HERDR_PANE_ID="", HERDR_PLUGIN_EVENT=hook["on"],
                HERDR_PLUGIN_EVENT_JSON=json.dumps({"data": data})))
        self.assertEqual(self.fetch_count(), 1)

    def test_sidebar_and_native_statusline_config(self):
        herdr = tomllib.loads((REPO_ROOT / "terminal/herdr/config.toml").read_text())
        self.assertIn(["$context_compact", "$monthly_credit"], herdr["ui"]["sidebar"]["agents"]["rows_by_agent"]["codex"])
        codex = tomllib.loads((REPO_ROOT / "ai/codex/config.toml").read_text())
        # Codex 0.164 rejects this item even though /status exposes monthly credit.
        self.assertNotIn("monthly-limit", codex["tui"]["status_line"])

    def test_refresh_finishes_before_context_copy_and_uses_target_pane(self):
        self.write_scenario(context="52%", refresh_delay=.1)
        report = self.run_hook(HERDR_PANE_ID="w1:p9", HERDR_PLUGIN_CONFIG_DIR="notify-config",
                               HERDR_PLUGIN_STATE_DIR="notify-state")
        self.assertIn("context_compact=💬52%", report)
        self.assertFalse(any(arg.startswith("context=") for arg in report))
        refresh_env = json.loads((self.root / "refresh_env").read_text())
        self.assertEqual(refresh_env, {"HERDR_PANE_ID": "w1:p9", "HERDR_PLUGIN_ACTION_ID": "refresh"})
        self.assertEqual(len(self.reports()), 1)

    def test_refresh_failure_hides_context_but_keeps_monthly_credit(self):
        self.write_scenario(refresh_fail=True)
        report = self.run_hook()
        self.assertIn("context_compact", report)
        self.assertNotIn("context_compact=💬31%", report)
        self.assertIn("monthly_credit=📅59%", report)

    def test_pane_lookup_failure_after_credit_read_clears_both_tokens(self):
        self.write_scenario(second_get_error=True)
        self.assert_cleared(self.run_hook(), codex=False)
