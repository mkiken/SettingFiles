import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
GSD_HELPER = REPO_ROOT / "mac/scripts/ai/gsd_core.sh"


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class GsdCoreSetupTest(unittest.TestCase):
    def run_helper(
        self,
        *arguments: str,
        home: str | None = None,
        reconcile_marker: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        # reconcile_marker: True の場合、restore/fixスタブが標準出力にマーカー行を
        # 出す。これでVERSIONガードの有無に関わらずrestore/fixが呼ばれたことを
        # npx引数出力（同じcaptured_argumentsに混在）と区別して検証できる。
        reconcile_marker_line = "REPO_ROOT_RECONCILE_CALLED" if reconcile_marker else ""
        script = f'''
source "{GSD_HELPER}"

function require_ai_setup_command() {{
  return 0
}}

function npx() {{
  printf '%s\\n' "$@"
}}

function _restore_managed_codex_gsd_hooks() {{
  {f'printf "%s\\n" "{reconcile_marker_line}"' if reconcile_marker else ""}
  return 0
}}

function _fix_claude_gsd_write_permissions() {{
  {f'printf "%s\\n" "{reconcile_marker_line}"' if reconcile_marker else ""}
  return 0
}}

setup_gsd_core_for_runtime "$@"
'''
        env = None
        if home is not None:
            env = {**os.environ, "HOME": home}

        result = subprocess.run(
            ["zsh", "-c", script, "gsd-core-test", *arguments],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
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
        failure: str = "",
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "repo"
            home = temp_root / "home"
            codex_dir = home / ".codex"
            managed_path = repo_root / "ai/codex/hooks.json"
            live_path = codex_dir / "hooks.json"
            trash_dir = temp_root / "trash"
            process_temp_dir = temp_root / "tmp"
            managed_path.parent.mkdir(parents=True)
            trash_dir.mkdir()
            process_temp_dir.mkdir()

            managed_hooks = json.loads(read_text("ai/codex/hooks.json"))
            live_hooks = json.loads(json.dumps(managed_hooks))

            def absolute_gsd_group(group: dict[str, object], hook_home: Path) -> dict[str, object]:
                absolute_group = json.loads(json.dumps(group))
                for hook in absolute_group["hooks"]:
                    command = hook["command"]
                    if command.startswith("node ~/.codex/hooks/gsd-"):
                        script_name = command.rsplit("/", 1)[1]
                        hook["command"] = (
                            f'"/opt/homebrew/bin/node" '
                            f'"{hook_home}/.codex/hooks/{script_name}"'
                        )
                return absolute_group

            def reordered_absolute_gsd_group(
                group: dict[str, object], hook_home: Path
            ) -> dict[str, object]:
                # 実際に gsd-core 1.7.0 が live に書き込む絶対パスグループの形を再現する:
                # command を書き換えるだけでなくキー挿入順を逆転させる（type を command より先に）。
                # jq の tojson はキー順を保持するため、これがないと dedup キー生成のバグ
                # （hook_key の tojson がキー順に依存していた）を再現できない。
                absolute_group = json.loads(json.dumps(group))
                reordered_hooks = []
                for hook in absolute_group["hooks"]:
                    command = hook["command"]
                    if command.startswith("node ~/.codex/hooks/gsd-"):
                        script_name = command.rsplit("/", 1)[1]
                        new_command = (
                            f'"/opt/homebrew/bin/node" '
                            f'"{hook_home}/.codex/hooks/{script_name}"'
                        )
                        reordered_hook = {"type": hook["type"], "command": new_command}
                        for key, value in hook.items():
                            if key not in ("command", "type"):
                                reordered_hook[key] = value
                        reordered_hooks.append(reordered_hook)
                    else:
                        reordered_hooks.append(hook)
                absolute_group["hooks"] = reordered_hooks
                return absolute_group

            def add_gsd_duplicates(copies: int) -> None:
                for groups in live_hooks["hooks"].values():
                    gsd_groups = [
                        group
                        for group in groups
                        if any(
                            hook["command"].startswith("node ~/.codex/hooks/gsd-")
                            for hook in group["hooks"]
                        )
                    ]
                    for group in gsd_groups:
                        groups.extend(
                            absolute_gsd_group(group, home)
                            for _ in range(copies)
                        )

            if variant == "portable-absolute-duplicate":
                add_gsd_duplicates(1)
            elif variant == "multiple-gsd-duplicates":
                add_gsd_duplicates(3)
            elif variant == "portable-absolute-duplicate-reordered-keys":
                # live 障害の再現: SessionStart の gsd-check-update グループ（timeout 無し、
                # キー順 command→type）に対し、キー順を逆転させた絶対パス複製を別グループとして追加。
                # canon 修正前はこの重複が dedup で消えず、live で観測された不一致を再現する。
                for groups in live_hooks["hooks"].values():
                    gsd_groups = [
                        group
                        for group in groups
                        if any(
                            hook["command"].startswith("node ~/.codex/hooks/gsd-")
                            for hook in group["hooks"]
                        )
                    ]
                    for group in gsd_groups:
                        groups.append(reordered_absolute_gsd_group(group, home))
            elif variant == "non-gsd-duplicate-reordered-keys":
                # canon が非GSDフックまで巻き込んで誤って縮約しないことの境界確認:
                # 非GSDグループのキー順を逆転させた複製でも「重複」とみなされず、
                # 依然として preserving で拒否されるべき（is_portable_gsd_hook ガードは不変）。
                notification_group = live_hooks["hooks"]["PermissionRequest"][0]
                reordered_group = json.loads(json.dumps(notification_group))
                reordered_group["hooks"] = [
                    {
                        key: hook[key]
                        for key in sorted(hook.keys(), reverse=True)
                    }
                    for hook in reordered_group["hooks"]
                ]
                live_hooks["hooks"]["PermissionRequest"].append(reordered_group)
            elif variant == "non-gsd-duplicate":
                notification_group = live_hooks["hooks"]["PermissionRequest"][0]
                live_hooks["hooks"]["PermissionRequest"].append(
                    json.loads(json.dumps(notification_group))
                )
            elif variant == "foreign-home":
                gsd_group = live_hooks["hooks"]["PreCompact"][0]
                live_hooks["hooks"]["PreCompact"][0] = absolute_gsd_group(
                    gsd_group,
                    Path("/Users/other"),
                )
            elif variant == "unknown-hook":
                live_hooks["hooks"]["SessionStart"].append(
                    {
                        "hooks": [
                            {
                                "command": "node ~/.codex/hooks/gsd-unknown.js",
                                "type": "command",
                            }
                        ]
                    }
                )
            elif variant == "missing-gsd":
                live_hooks["hooks"]["PreCompact"] = []
            elif variant == "missing-herdr":
                live_hooks["hooks"]["SessionStart"] = [
                    group
                    for group in live_hooks["hooks"]["SessionStart"]
                    if not any("herdr-agent-state.sh" in hook["command"] for hook in group["hooks"])
                ]

            managed_path.write_text(json.dumps(managed_hooks), encoding="utf-8")
            if variant == "correct-symlink":
                codex_dir.mkdir(parents=True)
                live_path.symlink_to(managed_path)
            elif variant == "wrong-symlink":
                codex_dir.mkdir(parents=True)
                unexpected_target = temp_root / "unexpected-hooks.json"
                unexpected_target.write_text(json.dumps(live_hooks), encoding="utf-8")
                live_path.symlink_to(unexpected_target)
            elif variant == "directory-symlink":
                external_codex_dir = temp_root / "external-codex"
                external_codex_dir.mkdir()
                (external_codex_dir / "hooks.json").write_text(
                    json.dumps(live_hooks),
                    encoding="utf-8",
                )
                home.mkdir(parents=True)
                codex_dir.symlink_to(external_codex_dir, target_is_directory=True)
            else:
                codex_dir.mkdir(parents=True)
                live_path.write_text(json.dumps(live_hooks), encoding="utf-8")
                live_path.chmod(0o640)

            def snapshot(target: Path) -> tuple[str, object]:
                if target.is_symlink():
                    return "symlink", str(target.readlink())
                if target.is_file():
                    return "file", (target.read_bytes(), target.stat().st_mode & 0o777)
                if target.is_dir():
                    return "directory", tuple(sorted(entry.name for entry in target.iterdir()))
                return "missing", None

            before_state = {
                "codex_dir": snapshot(codex_dir),
                "live": snapshot(live_path),
            }

            script = f'''
source "{GSD_HELPER}"

function require_ai_setup_command() {{
  return 0
}}

function trash() {{
  if [[ "$GSD_TEST_FAILURE" == "cleanup-trash" && "$1" == */gsd-codex-live-hooks.* ]]; then
    return 91
  fi
  if [[ "$GSD_TEST_FAILURE" == "backup-trash" && "$1" == *.gsd-backup.* ]]; then
    return 1
  fi
  /bin/mv "$1" "$GSD_TEST_TRASH_DIR/${{1:t}}.$$.$RANDOM"
}}

function _gsd_atomic_replace() {{
  if [[ "$GSD_TEST_FAILURE" == "mv" ]]; then
    return 92
  fi
  /bin/mv -f "$1" "$2"
}}

GSD_TEST_FAILURE="$3"
GSD_TEST_TRASH_DIR="$4"
TMPDIR="$5"
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
                    failure,
                    str(trash_dir),
                    str(process_temp_dir),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            state = {
                "before": before_state,
                "after": {
                    "codex_dir": snapshot(codex_dir),
                    "live": snapshot(live_path),
                },
                "managed_path": str(managed_path),
                "same_dir_artifacts": sorted(
                    entry.name
                    for entry in codex_dir.glob(".hooks.json.gsd-*")
                ),
                "normalization_artifacts": sorted(
                    str(entry)
                    for entry in process_temp_dir.glob("gsd-codex-*")
                ),
                "trash_artifacts": sorted(entry.name for entry in trash_dir.iterdir()),
            }

        return result, state

    def test_supported_runtimes_use_global_full_portable_install(self):
        expected_common_arguments = [
            "--yes",
            "@opengsd/gsd-core@latest",
        ]
        expected_install_arguments = [
            "--global",
            "--profile=full",
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

    def test_unknown_mode_fails_before_invoking_npx(self):
        result, captured_arguments = self.run_helper("codex", "bogus-mode")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(captured_arguments, [])
        self.assertIn("expected GSD Core mode", result.stderr)

    def test_install_mode_skips_when_already_set_up(self):
        for runtime in ("claude", "codex"):
            with self.subTest(runtime=runtime):
                with tempfile.TemporaryDirectory() as temp_dir:
                    home = Path(temp_dir)
                    version_dir = home / f".{runtime}" / "gsd-core"
                    version_dir.mkdir(parents=True)
                    (version_dir / "VERSION").write_text("1.7.0", encoding="utf-8")

                    result, captured_arguments = self.run_helper(
                        runtime, "install", home=str(home)
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("--portable-hooks", captured_arguments)
                    self.assertIn("already set up", result.stdout)

    def test_install_mode_runs_npx_when_not_yet_set_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)

            result, captured_arguments = self.run_helper(
                "codex", "install", home=str(home)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--portable-hooks", captured_arguments)

    def test_update_mode_always_runs_npx_even_if_already_set_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            version_dir = home / ".codex" / "gsd-core"
            version_dir.mkdir(parents=True)
            (version_dir / "VERSION").write_text("1.7.0", encoding="utf-8")

            result, captured_arguments = self.run_helper(
                "codex", "update", home=str(home)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--portable-hooks", captured_arguments)

    def test_default_mode_is_update_and_runs_npx_even_if_already_set_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            version_dir = home / ".codex" / "gsd-core"
            version_dir.mkdir(parents=True)
            (version_dir / "VERSION").write_text("1.7.0", encoding="utf-8")

            result, captured_arguments = self.run_helper("codex", home=str(home))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--portable-hooks", captured_arguments)

    def test_reconcile_runs_regardless_of_version_guard(self):
        # VERSIONガードはnpx再実行（重複フック書き込み防止）のみをスキップする
        # べきで、symlink復元（codex: _restore_managed_codex_gsd_hooks /
        # claude: _fix_claude_gsd_write_permissions）は常に実行されるべき。
        # (mode, version_exists) の4象限をテーブル駆動で検証する。
        cases = (
            # (mode, version_exists, expect_npx, expect_reconcile)
            ("install", True, False, True),
            ("install", False, True, True),
            ("update", True, True, True),
            ("update", False, True, True),
        )
        for runtime in ("claude", "codex"):
            for mode, version_exists, expect_npx, expect_reconcile in cases:
                with self.subTest(runtime=runtime, mode=mode, version_exists=version_exists):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        home = Path(temp_dir)
                        if version_exists:
                            version_dir = home / f".{runtime}" / "gsd-core"
                            version_dir.mkdir(parents=True)
                            (version_dir / "VERSION").write_text(
                                "1.7.0", encoding="utf-8"
                            )

                        result, captured_arguments = self.run_helper(
                            runtime, mode, home=str(home), reconcile_marker=True
                        )

                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(
                            "--portable-hooks" in captured_arguments, expect_npx
                        )
                        self.assertEqual(
                            "REPO_ROOT_RECONCILE_CALLED" in captured_arguments,
                            expect_reconcile,
                        )

    def test_install_mode_checks_runtime_specific_version_path(self):
        # claude 側に VERSION があっても codex install はスキップされない
        # （ランタイムごとに別パス ~/.<runtime>/gsd-core/VERSION を見る）。
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            claude_version_dir = home / ".claude" / "gsd-core"
            claude_version_dir.mkdir(parents=True)
            (claude_version_dir / "VERSION").write_text("1.7.0", encoding="utf-8")

            result, captured_arguments = self.run_helper(
                "codex", "install", home=str(home)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--portable-hooks", captured_arguments)

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
        self.assertIn('backup_file="$(mktemp "$live_dir/.${live_name}.gsd-backup.XXXXXX")"', helper)
        self.assertIn('/bin/ln -s "$managed_hooks" "$replacement_link"', helper)
        self.assertIn('_gsd_atomic_replace "$replacement_link" "$live_hooks"', helper)
        self.assertIn('/bin/mv -f "$backup_file" "$live_hooks"', helper)
        self.assertIn('_gsd_trash_artifact "$replacement_link"', helper)
        self.assertNotIn("/bin/rm", helper)
        self.assertLess(
            helper.index('cmp -s "$live_normalized" "$managed_normalized"'),
            helper.index('backup_file="$(mktemp "$live_dir/.${live_name}.gsd-backup.XXXXXX")"'),
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

    def test_hook_reconciliation_deduplicates_only_generated_gsd_hooks(self):
        for variant in (
            "portable-absolute-duplicate",
            "multiple-gsd-duplicates",
            "portable-absolute-duplicate-reordered-keys",
        ):
            with self.subTest(variant=variant):
                result, state = self.run_reconcile(variant)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    state["after"]["live"],
                    ("symlink", state["managed_path"]),
                )
                self.assertEqual(state["same_dir_artifacts"], [])
                self.assertEqual(state["normalization_artifacts"], [])
                self.assertTrue(
                    any("gsd-backup" in name for name in state["trash_artifacts"])
                )

    def test_hook_reconciliation_rejects_non_exact_managed_sets(self):
        cases = {
            "non-gsd-duplicate": "preserving",
            "non-gsd-duplicate-reordered-keys": "preserving",
            "foreign-home": "preserving",
            "unknown-hook": "preserving",
            "missing-gsd": "preserving",
            "missing-herdr": "preserving",
        }

        for variant, expected_error in cases.items():
            with self.subTest(variant=variant):
                result, state = self.run_reconcile(variant)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)
                self.assertEqual(state["after"], state["before"])
                self.assertEqual(state["same_dir_artifacts"], [])
                self.assertEqual(state["normalization_artifacts"], [])

    def test_hook_reconciliation_handles_symlinks_without_mutation(self):
        cases = {
            "correct-symlink": (0, ""),
            "wrong-symlink": (1, "unexpected symlink target"),
            "directory-symlink": (1, "directory is an unexpected symlink"),
        }

        for variant, (expected_rc, expected_error) in cases.items():
            with self.subTest(variant=variant):
                result, state = self.run_reconcile(variant)

                self.assertEqual(result.returncode, expected_rc, result.stderr)
                if expected_error:
                    self.assertIn(expected_error, result.stderr)
                self.assertEqual(state["after"], state["before"])
                self.assertEqual(state["same_dir_artifacts"], [])
                self.assertEqual(state["normalization_artifacts"], [])
                self.assertEqual(state["trash_artifacts"], [])

    def test_hook_reconciliation_rolls_back_replace_and_backup_trash_failures(self):
        for failure in ("mv", "backup-trash"):
            with self.subTest(failure=failure):
                result, state = self.run_reconcile(
                    "portable-absolute-duplicate",
                    failure=failure,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(state["before"]["live"][1][1], 0o640)
                self.assertEqual(
                    state["after"]["live"][1][1],
                    state["before"]["live"][1][1],
                )
                self.assertEqual(state["after"], state["before"])
                self.assertEqual(state["same_dir_artifacts"], [])
                self.assertEqual(state["normalization_artifacts"], [])

    def test_hook_reconciliation_reports_exact_cleanup_artifact(self):
        result, state = self.run_reconcile(
            "portable-absolute-duplicate",
            failure="cleanup-trash",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state["after"], state["before"])
        self.assertEqual(state["same_dir_artifacts"], [])
        self.assertEqual(len(state["normalization_artifacts"]), 1)
        self.assertIn(state["normalization_artifacts"][0], result.stderr)

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
                "setup_gsd_core_for_runtime claude install || exit 1",
                "setup_claude_mem",
            ),
            "mac/updates/claude.sh": (
                "setup_gsd_core_for_runtime claude update || exit 1",
                "setup_claude_mem",
            ),
            "mac/initialization/ai/codex.sh": (
                "setup_gsd_core_for_runtime codex install || exit 1",
                'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml',
            ),
            "mac/updates/codex.sh": (
                "setup_gsd_core_for_runtime codex update || exit 1",
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
