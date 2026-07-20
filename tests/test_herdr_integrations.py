import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HERDR_SCRIPT = REPO_ROOT / "mac" / "scripts" / "herdr.sh"
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def write_executable(file_path: Path, content: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)


def herdr_entry(runtime: str) -> dict:
    if runtime == "claude":
        return {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/herdr-agent-state.sh session",
                    "timeout": 10,
                }
            ],
        }
    return {
        "hooks": [
            {
                "type": "command",
                "command": "bash ~/.codex/herdr-agent-state.sh session",
                "timeout": 10,
            }
        ]
    }


class HerdrIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.fake_bin = self.root / "bin"
        self.tmp_dir = self.root / "tmp"
        self.invocation_log = self.root / "herdr-invocations.log"

        for directory in (self.fake_bin, self.tmp_dir, self.home / ".claude", self.home / ".codex"):
            directory.mkdir(parents=True, exist_ok=True)

        claude_settings = {
            "hooks": {
                "SessionStart": [herdr_entry("claude")],
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [{"type": "command", "command": "existing-claude-hook"}],
                    }
                ],
            }
        }
        codex_hooks = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "existing-codex-hook"}]},
                    herdr_entry("codex"),
                ]
            }
        }

        self.claude_source = self.repo / "ai" / "claude" / "settings.json"
        self.codex_hooks_source = self.repo / "ai" / "codex" / "hooks.json"
        self.codex_config_source = self.repo / "ai" / "codex" / "config.toml"
        for file_path, content in (
            (self.claude_source, json.dumps(claude_settings, indent=2)),
            (self.codex_hooks_source, json.dumps(codex_hooks, indent=2)),
            (self.codex_config_source, "[features]\nhooks = true\n"),
        ):
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")

        (self.home / ".claude" / "settings.json").write_text(
            self.claude_source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (self.home / ".codex" / "hooks.json").symlink_to(self.codex_hooks_source)
        (self.home / ".codex" / "config.toml").write_text(
            self.codex_config_source.read_text(encoding="utf-8"), encoding="utf-8"
        )

        write_executable(
            self.fake_bin / "trash",
            "#!/bin/sh\nexit 0\n",
        )
        write_executable(
            self.fake_bin / "herdr",
            """#!/bin/bash
set -eu
runtime="$3"
action="${HERDR_TEST_ACTION:-session}"
printf '%s|%s|%s|%s\n' "$runtime" "$HOME" "$CLAUDE_CONFIG_DIR" "$CODEX_HOME" >> "$HERDR_TEST_LOG"

if [[ "$runtime" == "claude" ]]; then
  hook="$CLAUDE_CONFIG_DIR/hooks/herdr-agent-state.sh"
  config="$CLAUDE_CONFIG_DIR/settings.json"
else
  hook="$CODEX_HOME/herdr-agent-state.sh"
  config="$CODEX_HOME/hooks.json"
fi
command_hook="$hook"
if [[ "${HERDR_TEST_PATH_ALIAS:-0}" == "1" ]]; then
  if [[ "$runtime" == "claude" ]]; then
    command_hook="${hook%/*}/../hooks/herdr-agent-state.sh"
  else
    command_hook="${hook%/*}/../codex/herdr-agent-state.sh"
  fi
fi
command="bash '$command_hook' $action"

printf '#!/bin/sh\n# staged %s hook\n' "$runtime" > "$hook"
chmod +x "$hook"
tmp_file="${config}.tmp"
if [[ "$runtime" == "claude" ]]; then
  /usr/bin/jq --arg command "$command" \
    '.hooks.SessionStart = ((.hooks.SessionStart // []) + [{"matcher":"*","hooks":[{"type":"command","command":$command,"timeout":10}]}])' \
    "$config" > "$tmp_file"
else
  /usr/bin/jq --arg command "$command" \
    '.hooks.SessionStart = ((.hooks.SessionStart // []) + [{"hooks":[{"type":"command","command":$command,"timeout":10}]}])' \
    "$config" > "$tmp_file"
fi
/bin/mv "$tmp_file" "$config"

if [[ "${HERDR_TEST_SCHEMA_MISMATCH:-0}" == "1" && "$runtime" == "codex" ]]; then
  tmp_file="${config}.tmp"
  /usr/bin/jq '.hooks.FutureEvent = [{"hooks":[]}]' "$config" > "$tmp_file"
  /bin/mv "$tmp_file" "$config"
fi
""",
        )

    def run_zsh(self, command: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.fake_bin}:{SYSTEM_PATH}",
                "TMPDIR": str(self.tmp_dir),
                "HERDR_TEST_LOG": str(self.invocation_log),
            }
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["zsh", "-fc", f'source "{HERDR_SCRIPT}"; {command}'],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def live_deployment_state(self) -> dict[str, tuple[object, ...]]:
        destinations = (
            self.home / ".claude" / "settings.json",
            self.home / ".claude" / "hooks" / "herdr-agent-state.sh",
            self.home / ".codex" / "herdr-agent-state.sh",
        )
        destination_directories = (
            self.home / ".claude",
            self.home / ".claude" / "hooks",
            self.home / ".codex",
        )
        state: dict[str, tuple[object, ...]] = {}
        for destination in destinations:
            if destination.is_symlink():
                state[str(destination)] = ("link", os.readlink(destination))
            elif destination.is_file():
                state[str(destination)] = (
                    "file",
                    stat.S_IMODE(destination.stat().st_mode),
                    destination.read_bytes(),
                )
            elif destination.exists():
                state[str(destination)] = ("other", "")
            else:
                state[str(destination)] = ("missing", "")
        for directory in destination_directories:
            key = f"directory:{directory}"
            if directory.is_symlink():
                state[key] = ("link", os.readlink(directory))
            elif directory.is_dir():
                state[key] = ("directory", stat.S_IMODE(directory.stat().st_mode))
            elif directory.exists():
                state[key] = ("other", "")
            else:
                state[key] = ("missing", "")
        return state

    def external_target_state(self, target: Path) -> tuple[object, ...]:
        if target.is_symlink():
            return ("link", os.readlink(target))
        if target.is_file():
            return ("file", stat.S_IMODE(target.stat().st_mode), target.read_bytes())
        if target.is_dir():
            entries = []
            for entry in sorted(target.rglob("*")):
                relative = str(entry.relative_to(target))
                if entry.is_symlink():
                    entries.append((relative, "link", os.readlink(entry)))
                elif entry.is_file():
                    entries.append(
                        (relative, "file", stat.S_IMODE(entry.stat().st_mode), entry.read_bytes())
                    )
                elif entry.is_dir():
                    entries.append((relative, "directory", stat.S_IMODE(entry.stat().st_mode)))
                else:
                    entries.append((relative, "other"))
            return ("directory", tuple(entries))
        return ("missing",)

    def live_deployment_artifacts(self) -> list[str]:
        directories = (
            self.home / ".claude",
            self.home / ".claude" / "hooks",
            self.home / ".codex",
        )
        return sorted(
            str(candidate)
            for directory in directories
            if directory.is_dir()
            for candidate in directory.glob(".*.herdr-*")
        )

    def test_stages_integrations_then_deploys_only_hook_scripts(self) -> None:
        claude_before = self.claude_source.read_bytes()
        codex_before = self.codex_hooks_source.read_bytes()

        result = self.run_zsh(f'setup_herdr_integrations "{self.repo}" "{self.home}"')

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("staged claude hook", (self.home / ".claude/hooks/herdr-agent-state.sh").read_text())
        self.assertIn("staged codex hook", (self.home / ".codex/herdr-agent-state.sh").read_text())
        self.assertEqual(self.claude_source.read_bytes(), claude_before)
        self.assertEqual(self.codex_hooks_source.read_bytes(), codex_before)
        self.assertTrue((self.home / ".codex/hooks.json").is_symlink())
        self.assertEqual((self.home / ".codex/hooks.json").resolve(), self.codex_hooks_source.resolve())
        self.assertEqual(self.live_deployment_artifacts(), [])

        invocations = self.invocation_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(invocations), 2)
        for invocation in invocations:
            self.assertNotIn(str(self.home), invocation)
            self.assertIn("settingfiles-herdr-integration", invocation)

    def test_schema_mismatches_fail_before_hook_deployment(self) -> None:
        mismatches = (
            {"HERDR_TEST_SCHEMA_MISMATCH": "1"},
            {"HERDR_TEST_ACTION": "working"},
            {"HERDR_TEST_ACTION": "session --verbose"},
            {"HERDR_TEST_PATH_ALIAS": "1"},
        )
        for extra_env in mismatches:
            with self.subTest(extra_env=extra_env):
                result = self.run_zsh(
                    f'setup_herdr_integrations "{self.repo}" "{self.home}"',
                    extra_env,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("schema differs", result.stderr)
                self.assertFalse((self.home / ".claude/hooks/herdr-agent-state.sh").exists())
                self.assertFalse((self.home / ".codex/herdr-agent-state.sh").exists())

    def test_shared_state_snapshot_hashes_regular_file_behind_symlink(self) -> None:
        live_settings = self.home / ".claude" / "settings.json"
        resolved_settings = self.root / "resolved-claude-settings.json"
        resolved_settings.write_text('{"version":1}\n', encoding="utf-8")
        live_settings.unlink()
        live_settings.symlink_to(resolved_settings)
        before_snapshot = self.root / "before-snapshot"
        after_snapshot = self.root / "after-snapshot"

        before_result = self.run_zsh(
            f'_herdr_shared_state_snapshot "{before_snapshot}" "{self.home}"'
        )
        self.assertEqual(before_result.returncode, 0, before_result.stderr)

        before_line = next(
            line
            for line in before_snapshot.read_text(encoding="utf-8").splitlines()
            if str(live_settings) in line
        )
        expected_hash = hashlib.sha256(resolved_settings.read_bytes()).hexdigest()
        self.assertEqual(
            before_line,
            f"link|{live_settings}|{resolved_settings}|file|{expected_hash}",
        )

        resolved_settings.write_text('{"version":2}\n', encoding="utf-8")
        after_result = self.run_zsh(
            f'_herdr_shared_state_snapshot "{after_snapshot}" "{self.home}"'
        )
        self.assertEqual(after_result.returncode, 0, after_result.stderr)
        self.assertNotEqual(before_snapshot.read_bytes(), after_snapshot.read_bytes())

    def test_live_claude_registration_is_created_upgraded_and_idempotent(self) -> None:
        live_settings = self.home / ".claude" / "settings.json"
        stop_entry = {
            "matcher": "",
            "hooks": [{"type": "command", "command": "keep-stop-hook"}],
        }
        other_session_entry = {
            "matcher": "startup",
            "hooks": [{"type": "command", "command": "keep-session-hook"}],
        }
        old_mixed_entry = {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/herdr-agent-state.sh working",
                    "timeout": 10,
                },
                {"type": "command", "command": "keep-sibling-hook"},
            ],
        }
        cases = (
            ("new settings", None, set()),
            (
                "missing registration",
                {
                    "machineLocal": True,
                    "hooks": {
                        "SessionStart": [other_session_entry],
                        "Stop": [stop_entry],
                    },
                },
                {"keep-session-hook", "keep-stop-hook"},
            ),
            (
                "old registration",
                {
                    "machineLocal": True,
                    "hooks": {
                        "SessionStart": [old_mixed_entry, other_session_entry],
                        "Stop": [stop_entry],
                    },
                },
                {"keep-sibling-hook", "keep-session-hook", "keep-stop-hook"},
            ),
        )

        for name, initial_settings, preserved_commands in cases:
            with self.subTest(case=name):
                if live_settings.exists():
                    live_settings.unlink()
                if initial_settings is not None:
                    live_settings.write_text(
                        json.dumps(initial_settings, indent=2) + "\n",
                        encoding="utf-8",
                    )

                first_result = self.run_zsh(
                    f'setup_herdr_integrations "{self.repo}" "{self.home}"'
                )
                self.assertEqual(first_result.returncode, 0, first_result.stderr)
                first_bytes = live_settings.read_bytes()

                second_result = self.run_zsh(
                    f'setup_herdr_integrations "{self.repo}" "{self.home}"'
                )
                self.assertEqual(second_result.returncode, 0, second_result.stderr)
                self.assertEqual(live_settings.read_bytes(), first_bytes)

                deployed = json.loads(first_bytes)
                all_commands = {
                    hook["command"]
                    for entries in deployed.get("hooks", {}).values()
                    for entry in entries
                    for hook in entry.get("hooks", [])
                    if "command" in hook
                }
                herdr_commands = {
                    command for command in all_commands if "herdr-agent-state.sh" in command
                }
                self.assertEqual(
                    herdr_commands,
                    {"bash ~/.claude/hooks/herdr-agent-state.sh session"},
                )
                self.assertTrue(preserved_commands.issubset(all_commands))
                if initial_settings is not None:
                    self.assertTrue(deployed["machineLocal"])

    def test_claude_settings_atomic_candidate_uses_private_or_existing_mode(self) -> None:
        live_settings = self.home / ".claude" / "settings.json"
        mode_log = self.root / "claude-settings-candidate-mode"
        cases = (
            ("existing 0600", 0o600, 0o600),
            ("existing 0640", 0o640, 0o640),
            ("new settings", None, 0o600),
        )
        override = f'''
            _herdr_atomic_replace() {{
              if [[ "$2" == "{live_settings}" ]]; then
                /usr/bin/stat -f '%Lp' "$1" >| "$HERDR_MODE_LOG"
              fi
              /bin/mv -f "$1" "$2"
            }}
        '''

        for name, initial_mode, expected_mode in cases:
            with self.subTest(case=name):
                if live_settings.exists():
                    live_settings.unlink()
                if initial_mode is not None:
                    live_settings.write_bytes(self.claude_source.read_bytes())
                    live_settings.chmod(initial_mode)
                if mode_log.exists():
                    mode_log.unlink()

                result = self.run_zsh(
                    override
                    + f'\nsetup_herdr_integrations "{self.repo}" "{self.home}"',
                    {"HERDR_MODE_LOG": str(mode_log)},
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(stat.S_IMODE(live_settings.stat().st_mode), expected_mode)
                self.assertEqual(int(mode_log.read_text(encoding="utf-8").strip(), 8), expected_mode)
                self.assertEqual(self.live_deployment_artifacts(), [])

    def test_deployment_failures_leave_all_live_destinations_unchanged(self) -> None:
        live_settings = self.home / ".claude" / "settings.json"
        claude_hooks_dir = self.home / ".claude" / "hooks"
        claude_hook = claude_hooks_dir / "herdr-agent-state.sh"
        codex_dir = self.home / ".codex"
        codex_hook = codex_dir / "herdr-agent-state.sh"
        settings_baseline = live_settings.read_bytes()
        copy_failure = '''
            _herdr_copy_deployment_file() {
              if [[ "$1" == */codex/herdr-agent-state.sh ]]; then
                return 91
              fi
              /bin/cp -p "$1" "$2"
            }
        '''
        move_failure = f'''
            _herdr_atomic_replace() {{
              if [[ "$2" == "{codex_hook}" ]]; then
                return 92
              fi
              /bin/mv -f "$1" "$2"
            }}
        '''
        cases = (
            ("hook file symlink", "hook_symlink", "directory", ""),
            ("candidate copy failure", "missing_hook", "directory", copy_failure),
            ("missing hooks directory rollback", "missing_directory", "directory", move_failure),
            ("existing Claude hook rollback", "existing_hook", "directory", move_failure),
            ("Claude hooks directory symlink", "directory_symlink", "directory", ""),
            ("Codex directory symlink", "missing_hook", "directory_symlink", ""),
        )

        for name, claude_initial, codex_initial, override in cases:
            with self.subTest(case=name):
                if claude_hooks_dir.is_symlink():
                    claude_hooks_dir.unlink()
                elif claude_hooks_dir.is_dir():
                    for child in claude_hooks_dir.iterdir():
                        child.unlink()
                    claude_hooks_dir.rmdir()
                if codex_dir.is_symlink():
                    codex_target = Path(os.readlink(codex_dir))
                    codex_dir.unlink()
                    codex_target.rename(codex_dir)
                if codex_hook.exists() or codex_hook.is_symlink():
                    codex_hook.unlink()
                live_settings.write_bytes(settings_baseline)

                external_targets: list[Path] = []
                if claude_initial == "hook_symlink":
                    claude_hooks_dir.mkdir()
                    hook_target = self.root / f"{name}-target.sh"
                    hook_target.write_text("#!/bin/sh\n# user-owned\n", encoding="utf-8")
                    claude_hook.symlink_to(hook_target)
                    external_targets.append(hook_target)
                elif claude_initial == "missing_hook":
                    claude_hooks_dir.mkdir()
                elif claude_initial == "existing_hook":
                    claude_hooks_dir.mkdir()
                    claude_hook.write_text("#!/bin/sh\n# existing\n", encoding="utf-8")
                    claude_hook.chmod(0o750)
                elif claude_initial == "directory_symlink":
                    hooks_target = self.root / f"{name}-target"
                    hooks_target.mkdir()
                    (hooks_target / "sentinel").write_text("unchanged\n", encoding="utf-8")
                    claude_hooks_dir.symlink_to(hooks_target)
                    external_targets.append(hooks_target)

                if codex_initial == "directory_symlink":
                    codex_target = self.root / f"{name}-target"
                    codex_dir.rename(codex_target)
                    codex_dir.symlink_to(codex_target)
                    external_targets.append(codex_target)

                before = self.live_deployment_state()
                target_before = {
                    str(target): self.external_target_state(target) for target in external_targets
                }
                result = self.run_zsh(
                    override
                    + f'\nsetup_herdr_integrations "{self.repo}" "{self.home}"'
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.live_deployment_state(), before)
                self.assertEqual(
                    {str(target): self.external_target_state(target) for target in external_targets},
                    target_before,
                )
                self.assertEqual(self.live_deployment_artifacts(), [])

    def test_config_symlink_is_idempotent_and_protects_existing_file(self) -> None:
        config_source = self.repo / "terminal" / "herdr" / "config.toml"
        config_source.parent.mkdir(parents=True, exist_ok=True)
        config_source.write_text("onboarding = false\n", encoding="utf-8")
        live_config = self.home / ".config" / "herdr" / "config.toml"

        setup_command = (
            'make_symlink() { /bin/ln -s "$1" "$2"; }; '
            f'setup_herdr_config "{self.repo}" "{self.home}"; '
            f'setup_herdr_config "{self.repo}" "{self.home}"'
        )
        result = self.run_zsh(setup_command)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(live_config.is_symlink())
        self.assertEqual(live_config.resolve(), config_source.resolve())

        live_config.unlink()
        live_config.write_text("user-owned = true\n", encoding="utf-8")
        result = self.run_zsh(
            'make_symlink() { return 99; }; '
            f'setup_herdr_config "{self.repo}" "{self.home}"'
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(live_config.read_text(encoding="utf-8"), "user-owned = true\n")

    def test_unexpected_codex_hooks_link_fails_before_installer(self) -> None:
        live_hooks = self.home / ".codex" / "hooks.json"
        live_hooks.unlink()
        unexpected_hooks = self.root / "unexpected-hooks.json"
        unexpected_hooks.write_text(self.codex_hooks_source.read_text(encoding="utf-8"), encoding="utf-8")
        live_hooks.symlink_to(unexpected_hooks)

        result = self.run_zsh(f'setup_herdr_integrations "{self.repo}" "{self.home}"')

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected symlink target", result.stderr)
        self.assertFalse(self.invocation_log.exists())
        self.assertFalse((self.home / ".claude/hooks/herdr-agent-state.sh").exists())
        self.assertFalse((self.home / ".codex/herdr-agent-state.sh").exists())

    def test_only_supported_integrations_are_installed(self) -> None:
        script = HERDR_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("integration install claude", script)
        self.assertIn("integration install codex", script)
        self.assertNotIn("integration install gemini", script)

        claude = json.loads((REPO_ROOT / "ai/claude/settings.json").read_text(encoding="utf-8"))
        codex = json.loads((REPO_ROOT / "ai/codex/hooks.json").read_text(encoding="utf-8"))
        self.assertIn(herdr_entry("claude"), claude["hooks"]["SessionStart"])
        self.assertIn(herdr_entry("codex"), codex["hooks"]["SessionStart"])


if __name__ == "__main__":
    unittest.main()
