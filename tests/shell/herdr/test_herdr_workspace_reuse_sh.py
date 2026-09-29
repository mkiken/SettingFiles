"""Named Herdr workspace creation and reuse."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


SCRIPT = REPO_ROOT / "shell/herdr/herdr-workspace-reuse.sh"


class HerdrWorkspaceReuseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "calls"
        self.fake = self.root / "herdr"
        self.fake.write_text(
            "#!/bin/bash\n"
            "printf '%s\\n' \"$*\" >> \"$TEST_CALLS\"\n"
            "case \"$1 $2\" in\n"
            "  'workspace list') [[ ${TEST_LIST_FAIL:-0} == 1 ]] && exit 1; "
            "printf '%s\\n' \"$TEST_LIST\" ;;\n"
            "  'workspace create') printf '%s\\n' \"$TEST_CREATE\" ;;\n"
            "  'workspace focus') [[ ${TEST_FOCUS_FAIL:-0} == 1 ]] && exit 1; "
            "printf '{\"result\":{}}\\n' ;;\n"
            "  *) printf '{\"result\":{}}\\n' ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        self.fake.chmod(0o755)
        self.created = {"result": {"workspace": {"workspace_id": "new"},
                                   "tab": {"tab_id": "t0"},
                                   "root_pane": {"pane_id": "p0"}}}

    def run_proxy(self, *args, workspaces=(), **env_extra):
        env = sanitized_env({
            "HERDR_REAL_BIN_PATH": str(self.fake),
            "TEST_CALLS": str(self.log),
            "TEST_LIST": json.dumps({"result": {"workspaces": list(workspaces)}}),
            "TEST_CREATE": json.dumps(self.created),
            **env_extra,
        })
        result = subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, env=env,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_new_named_workspace_preserves_create_arguments(self):
        result, calls = self.run_proxy(
            "workspace", "create", "--cwd", "/tmp/a", "--label", "Review",
            "--env", "A=B", "--no-focus",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["workspace list", "workspace create --cwd /tmp/a --label Review --env A=B --no-focus"])
        self.assertFalse(json.loads(result.stdout)["result"]["reused"])

    def test_exact_match_focuses_without_creating(self):
        existing = {"workspace_id": "old", "label": "[2] Review", "number": 2, "focused": False}
        result, calls = self.run_proxy("workspace", "create", "--label", "Review", "--focus", workspaces=[existing])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["workspace list", "workspace focus old"])
        self.assertEqual(json.loads(result.stdout)["result"], {"workspace": existing, "reused": True})

    def test_no_focus_reuses_without_focus_or_create(self):
        existing = {"workspace_id": "old", "label": "Review", "number": 1, "focused": False}
        result, calls = self.run_proxy("workspace", "create", "--label", "Review", "--no-focus", workspaces=[existing])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["workspace list"])

    def test_partial_and_case_mismatch_create_new(self):
        existing = {"workspace_id": "old", "label": "Review-extra", "number": 1, "focused": False}
        for label in ("Review", "review-extra"):
            with self.subTest(label=label):
                self.log.unlink(missing_ok=True)
                result, calls = self.run_proxy("workspace", "create", "--label", label, workspaces=[existing])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls[0], "workspace list")
                self.assertTrue(calls[1].startswith("workspace create "))

    def test_duplicate_prefers_focused_then_lowest_number(self):
        rows = [
            {"workspace_id": "high", "label": "Review", "number": 7, "focused": False},
            {"workspace_id": "low", "label": "Review", "number": 2, "focused": False},
            {"workspace_id": "focused", "label": "Review", "number": 9, "focused": True},
        ]
        for candidates, chosen in ((rows, "focused"), (rows[:2], "low")):
            with self.subTest(chosen=chosen):
                self.log.unlink(missing_ok=True)
                result, calls = self.run_proxy("workspace", "create", "--label", "Review", "--focus", workspaces=candidates)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, ["workspace list", f"workspace focus {chosen}"])

    def test_lookup_and_focus_fail_closed(self):
        existing = {"workspace_id": "old", "label": "Review", "number": 1, "focused": False}
        for extra in ({"TEST_LIST_FAIL": "1"}, {"TEST_LIST": "{bad"}, {"TEST_FOCUS_FAIL": "1"}):
            with self.subTest(extra=extra):
                self.log.unlink(missing_ok=True)
                result, calls = self.run_proxy("workspace", "create", "--label", "Review", "--focus", workspaces=[existing], **extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(c.startswith("workspace create ") for c in calls))

    def test_other_commands_and_unnamed_create_pass_through(self):
        for args in (("tab", "create", "--label", "x"), ("pane", "split", "--focus"), ("workspace", "create", "--cwd", "/tmp")):
            with self.subTest(args=args):
                self.log.unlink(missing_ok=True)
                result, calls = self.run_proxy(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, [" ".join(args)])

    def test_proxy_rejects_recursive_real_binary(self):
        result, calls = self.run_proxy(
            "workspace", "create", "--label", "Review",
            HERDR_REAL_BIN_PATH=str(SCRIPT),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("points to the proxy", result.stderr)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
