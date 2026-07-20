import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GSD_HELPER = REPO_ROOT / "mac/scripts/ai/gsd_core.sh"


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class GsdCoreSetupTest(unittest.TestCase):
    def run_helper(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        script = f'''
source "{GSD_HELPER}"

function require_ai_setup_command() {{
  return 0
}}

function npx() {{
  printf '%s\\n' "$@"
}}

function _restore_managed_codex_gsd_hooks() {{
  return 0
}}

setup_gsd_core_for_runtime "$@"
'''
        result = subprocess.run(
            ["zsh", "-c", script, "gsd-core-test", *arguments],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        captured_arguments = result.stdout.splitlines()

        return result, captured_arguments

    def normalize_hook_command(self, command: str, home: str) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.json"
            output_path = Path(temp_dir) / "normalized.json"
            source_path.write_text(
                json.dumps({"command": command}),
                encoding="utf-8",
            )
            script = f'''
source "{GSD_HELPER}"
_normalize_codex_gsd_hooks "$2" "$3" "$1"
'''
            result = subprocess.run(
                [
                    "zsh",
                    "-c",
                    script,
                    "gsd-normalize-test",
                    home,
                    str(source_path),
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(output_path.read_text(encoding="utf-8"))["command"]

    def run_reconcile(
        self,
        variant: str,
        *,
        trash_succeeds: bool = True,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repo"
            home = temp_root / "home"
            managed_path = repo_root / "ai/codex/hooks.json"
            live_path = home / ".codex/hooks.json"
            managed_path.parent.mkdir(parents=True)
            live_path.parent.mkdir(parents=True)

            managed_hooks = json.loads(read_text("ai/codex/hooks.json"))
            live_hooks = json.loads(json.dumps(managed_hooks))
            for groups in live_hooks["hooks"].values():
                for group in groups:
                    for hook in group["hooks"]:
                        command = hook["command"]
                        if command.startswith("node ~/.codex/hooks/gsd-"):
                            script_name = command.rsplit("/", 1)[1]
                            hook["command"] = (
                                f'"/opt/homebrew/bin/node" '
                                f'"{home}/.codex/hooks/{script_name}"'
                            )

            managed_path.write_text(json.dumps(managed_hooks), encoding="utf-8")
            if variant == "unexpected-symlink":
                unexpected_target = temp_root / "unexpected-hooks.json"
                unexpected_target.write_text(json.dumps(live_hooks), encoding="utf-8")
                live_path.symlink_to(unexpected_target)
            else:
                if variant == "mismatch":
                    live_hooks["hooks"]["UnknownUpstreamEvent"] = []
                live_path.write_text(json.dumps(live_hooks), encoding="utf-8")

            script = f'''
source "{GSD_HELPER}"

function require_ai_setup_command() {{
  return 0
}}

function trash() {{
  if [[ "$GSD_TEST_TRASH_SUCCEEDS" != "yes" ]]; then
    return 1
  fi
  /bin/mv "$1" "$1.trashed"
}}

GSD_TEST_TRASH_SUCCEEDS="$3"
_restore_managed_codex_gsd_hooks "$1" "$2"
'''
            result = subprocess.run(
                [
                    "zsh",
                    "-c",
                    script,
                    "gsd-reconcile-test",
                    str(repo_root),
                    str(home),
                    "yes" if trash_succeeds else "no",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            state = {
                "live_exists": live_path.exists() or live_path.is_symlink(),
                "live_is_symlink": live_path.is_symlink(),
                "live_target": str(live_path.readlink()) if live_path.is_symlink() else None,
                "managed_path": str(managed_path),
                "trashed_exists": Path(f"{live_path}.trashed").exists(),
                "replacement_links": list(live_path.parent.glob("hooks.json.gsd-managed-link.*")),
            }

        return result, state

    def test_supported_runtimes_use_global_standard_portable_install(self):
        expected_common_arguments = [
            "--yes",
            "@opengsd/gsd-core@latest",
        ]
        expected_install_arguments = [
            "--global",
            "--profile=standard",
            "--portable-hooks",
        ]

        for runtime in ("claude", "codex"):
            with self.subTest(runtime=runtime):
                result, arguments = self.run_helper(runtime)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    arguments,
                    expected_common_arguments
                    + [f"--{runtime}"]
                    + expected_install_arguments,
                )

    def test_missing_or_unknown_runtime_fails_before_invoking_npx(self):
        for arguments in ((), ("gemini",)):
            with self.subTest(arguments=arguments):
                result, captured_arguments = self.run_helper(*arguments)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(captured_arguments, [])
                self.assertIn("expected GSD Core runtime", result.stderr)

    def test_installer_is_noninteractive_and_checks_required_commands(self):
        helper = GSD_HELPER.read_text(encoding="utf-8")

        self.assertIn("require_ai_setup_command npx || return 1", helper)
        self.assertIn('require_ai_setup_command "$runtime" || return 1', helper)
        self.assertIn("--portable-hooks < /dev/null || return 1", helper)

    def test_codex_install_reconciles_generated_hooks_safely(self):
        helper = GSD_HELPER.read_text(encoding="utf-8")

        self.assertIn('if [[ "$runtime" == "codex" ]]', helper)
        self.assertIn("_restore_managed_codex_gsd_hooks || return 1", helper)
        self.assertIn("_normalize_codex_gsd_hooks", helper)
        self.assertIn('jq --sort-keys . "$managed_hooks"', helper)
        self.assertIn('cmp -s "$live_normalized" "$managed_normalized"', helper)
        self.assertIn("preserving $live_hooks for review", helper)
        self.assertIn('if ! trash "$live_hooks"; then', helper)
        self.assertIn('/bin/ln -s "$managed_hooks" "$replacement_link"', helper)
        self.assertIn('/bin/mv "$replacement_link" "$live_hooks"', helper)
        self.assertLess(
            helper.index('cmp -s "$live_normalized" "$managed_normalized"'),
            helper.index('if ! trash "$live_hooks"; then'),
        )

    def test_hook_normalization_requires_current_home_and_absolute_node(self):
        home = "/Users/gsd-test"
        portable_command = "node ~/.codex/hooks/gsd-context-monitor.js"
        cases = {
            "expected paths": (
                f'"/opt/homebrew/bin/node" "{home}/.codex/hooks/gsd-context-monitor.js"',
                portable_command,
            ),
            "foreign home": (
                '"/opt/homebrew/bin/node" "/Users/other/.codex/hooks/gsd-context-monitor.js"',
                '"/opt/homebrew/bin/node" "/Users/other/.codex/hooks/gsd-context-monitor.js"',
            ),
            "relative node": (
                f'"relative/node" "{home}/.codex/hooks/gsd-context-monitor.js"',
                f'"relative/node" "{home}/.codex/hooks/gsd-context-monitor.js"',
            ),
            "already portable": (portable_command, portable_command),
        }

        for name, (command, expected) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.normalize_hook_command(command, home), expected)

    def test_hook_reconciliation_restores_only_an_exact_generated_file(self):
        result, state = self.run_reconcile("matching")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(state["live_is_symlink"])
        self.assertEqual(state["live_target"], state["managed_path"])
        self.assertTrue(state["trashed_exists"])
        self.assertEqual(state["replacement_links"], [])

    def test_hook_reconciliation_preserves_mismatch_and_unexpected_link(self):
        for variant, expected_error in (
            ("mismatch", "preserving"),
            ("unexpected-symlink", "unexpected symlink target"),
        ):
            with self.subTest(variant=variant):
                result, state = self.run_reconcile(variant)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)
                self.assertTrue(state["live_exists"])
                self.assertFalse(state["trashed_exists"])
                self.assertEqual(state["replacement_links"], [])

    def test_hook_reconciliation_preserves_live_file_when_trash_fails(self):
        result, state = self.run_reconcile("matching", trash_succeeds=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(state["live_exists"])
        self.assertFalse(state["live_is_symlink"])
        self.assertFalse(state["trashed_exists"])
        self.assertEqual(state["replacement_links"], [])

    def test_managed_codex_gsd_hooks_are_portable_and_match_current_events(self):
        hooks = json.loads(read_text("ai/codex/hooks.json"))["hooks"]
        context_monitor = "node ~/.codex/hooks/gsd-context-monitor.js"
        update_check = "node ~/.codex/hooks/gsd-check-update.js"
        expected_commands = {
            "PermissionRequest": context_monitor,
            "PostCompact": context_monitor,
            "PostToolUse": context_monitor,
            "PreCompact": context_monitor,
            "PreToolUse": context_monitor,
            "SessionStart": update_check,
            "Stop": context_monitor,
            "SubagentStart": context_monitor,
            "SubagentStop": context_monitor,
            "UserPromptSubmit": context_monitor,
        }
        actual_hooks = {}

        for event, groups in hooks.items():
            for group in groups:
                for hook in group["hooks"]:
                    command = hook["command"]
                    self.assertNotIn("/Users/", command)
                    self.assertNotIn("/opt/", command)
                    if "gsd-" in command:
                        actual_hooks.setdefault(event, []).append(hook)

        self.assertEqual(set(actual_hooks), set(expected_commands))
        for event, expected_command in expected_commands.items():
            with self.subTest(event=event):
                self.assertEqual(len(actual_hooks[event]), 1)
                hook = actual_hooks[event][0]
                self.assertEqual(hook["command"], expected_command)
                self.assertEqual(hook["type"], "command")
                if expected_command == context_monitor:
                    self.assertEqual(hook["timeout"], 10)
                else:
                    self.assertNotIn("timeout", hook)

    def test_managed_codex_hooks_preserve_notification_commands(self):
        hooks = json.loads(read_text("ai/codex/hooks.json"))["hooks"]
        expected_commands = {
            "PermissionRequest": ["~/.codex/hooks/codex-stop-notification.sh"],
            "PostToolUse": [
                "~/.codex/hooks/codex-context-alert.sh",
                "python3 ~/.codex/hooks/codex-hook.py",
            ],
            "Stop": [
                "~/.codex/hooks/codex-stop-notification.sh",
                "~/.codex/hooks/codex-context-alert.sh",
            ],
            "UserPromptSubmit": [
                "~/.codex/hooks/codex-context-alert.sh",
                "python3 ~/.codex/hooks/codex-hook.py",
            ],
        }
        actual_commands = {}

        for event, groups in hooks.items():
            commands = [
                    hook["command"]
                    for group in groups
                    for hook in group["hooks"]
                    if "gsd-" not in hook["command"]
                    and "herdr-agent-state.sh" not in hook["command"]
            ]
            if commands:
                actual_commands[event] = commands

        self.assertEqual(actual_commands, expected_commands)

    def test_platform_helpers_source_the_shared_gsd_helper(self):
        source_line = 'source "${Repo}mac/scripts/ai/gsd_core.sh"'

        for script_path in (
            "mac/scripts/ai/claude.sh",
            "mac/scripts/ai/codex.sh",
        ):
            with self.subTest(script=script_path):
                self.assertEqual(read_text(script_path).count(source_line), 1)

    def test_initialization_and_updates_install_gsd_once_after_existing_setup(self):
        expected_scripts = {
            "mac/initialization/ai/claude.sh": (
                "setup_gsd_core_for_runtime claude || exit 1",
                "setup_claude_mem",
            ),
            "mac/updates/claude.sh": (
                "setup_gsd_core_for_runtime claude || exit 1",
                "setup_claude_mem",
            ),
            "mac/initialization/ai/codex.sh": (
                "setup_gsd_core_for_runtime codex || exit 1",
                'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml',
            ),
            "mac/updates/codex.sh": (
                "setup_gsd_core_for_runtime codex || exit 1",
                'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml',
            ),
        }

        for script_path, (install_line, earlier_line) in expected_scripts.items():
            script = read_text(script_path)
            with self.subTest(script=script_path):
                self.assertEqual(script.count(install_line), 1)
                self.assertLess(script.index(earlier_line), script.index(install_line))
                self.assertLess(script.index(install_line), script.rindex("echo"))

    def test_existing_sdd_tools_remain_managed(self):
        for script_path in (
            "mac/initialization/ai/codex.sh",
            "mac/updates/codex.sh",
        ):
            with self.subTest(script=script_path):
                self.assertIn("npx --yes cc-sdd@latest --codex-skills", read_text(script_path))

        claude_initialization = read_text("mac/initialization/ai/claude.sh")
        self.assertIn("tsumiki@tsumiki", claude_initialization)


if __name__ == "__main__":
    unittest.main()
