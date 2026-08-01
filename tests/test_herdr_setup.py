import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def run_zsh(script: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in ("FILTER_COMMAND", "FILTER_TOOL", "HERDR_ENV", "TMUX", "TMUX_PANE"):
        env.pop(name, None)
    env.update({"PATH": SYSTEM_PATH})
    env.update(env_overrides or {})

    return subprocess.run(
        ["/bin/zsh", "-fc", script],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class HerdrConfigurationTest(unittest.TestCase):
    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_managed_config_uses_selected_terminal_defaults(self):
        config = tomllib.loads(read_text("terminal/herdr/config.toml"))

        self.assertFalse(config["onboarding"])
        self.assertEqual(config["theme"]["name"], "terminal")
        self.assertEqual(
            config["terminal"],
            {
                "default_shell": "zsh",
                "shell_mode": "auto",
                "new_cwd": "follow",
            },
        )
        self.assertEqual(config["ui"]["toast"], {"delivery": "off", "delay_seconds": 1})
        self.assertTrue(config["ui"]["sound"]["enabled"])
        self.assertTrue(config["session"]["resume_agents_on_restore"])
        self.assertEqual(config["advanced"]["scrollback_limit_bytes"], 104857600)
        self.assertTrue(config["experimental"]["pane_history"])

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_sidebar_spaces_includes_shell_status_token(self):
        # $shell_status はherdr_status_icon.shがreport-metadataで書くworkspace
        # トークン列（shell以外のAI状態と併記して同列に表示する）。
        rows = tomllib.loads(read_text("terminal/herdr/config.toml"))["ui"]["sidebar"]["spaces"]["rows"]
        flattened = [cell for row in rows for cell in row]
        self.assertIn("$shell_status", flattened)
        self.assertIn("state_icon", flattened)

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_managed_config_maps_basic_tmux_style_keys(self):
        # config.tomlはHerdrデフォルト(146バインド)からのオーバーライドのみを列挙する方針
        # (CLAUDE.md参照)のため、keys全体の完全一致ではなく代表バインドをスポット検証する。
        keys = tomllib.loads(read_text("terminal/herdr/config.toml"))["keys"]

        self.assertEqual(keys["prefix"], "ctrl+t")

        expected_bindings = (
            ("navigate_pane_up", ["k", "ctrl+p"]),
            ("navigate_pane_down", ["j", "ctrl+n"]),
            ("next_workspace", "prefix+shift+n"),
            ("previous_workspace", "prefix+shift+p"),
            ("new_workspace", "prefix+shift+c"),
            ("switch_workspace", "prefix+shift+1..9"),
            ("open_worktree", "prefix+shift+o"),
            ("focus_agent", "prefix+ctrl+1..9"),
            ("next_agent", "prefix+ctrl+n"),
            ("previous_agent", "prefix+ctrl+p"),
        )
        for name, value in expected_bindings:
            with self.subTest(binding=name):
                self.assertEqual(keys[name], value)

        # [[keys.command]]ポップアップ群は個数を固定せず、代表エントリの存在のみ確認する
        self.assertTrue(any(c["key"] == "prefix+ctrl+g" for c in keys["command"]))

    def test_brewfile_and_entrypoints_keep_tmux_beside_herdr(self):
        brewfile = read_text("mac/Brewfile")
        initialize = read_text("mac/initialization/initialize")
        update = read_text("mac/update")

        self.assertEqual(brewfile.count('brew "herdr"'), 1)
        self.assertEqual(brewfile.count('brew "tmux"'), 1)
        self.assertTrue((REPO_ROOT / ".tmux.conf").is_file())
        self.assertEqual(initialize.count('source "${SCRIPT_DIR}/herdr.sh"'), 1)
        self.assertGreater(
            initialize.index('source "${SCRIPT_DIR}/herdr.sh"'),
            initialize.index('source "${SCRIPT_DIR}/ai/codex.sh"'),
        )
        self.assertEqual(update.count('source "$(dirname "$0")/updates/herdr.sh"'), 1)
        self.assertGreater(
            update.index('source "$(dirname "$0")/updates/herdr.sh"'),
            update.index('source "$(dirname "$0")/updates/codex.sh"'),
        )


class HerdrShellStartupTest(unittest.TestCase):
    def run_auto_start(
        self,
        *,
        herdr_rc: int | None = 0,
        include_tmux: bool = True,
        is_tmux: bool = False,
        is_ide: bool = False,
        is_warp: bool = False,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        definitions = []
        if herdr_rc is not None:
            definitions.append(f"function herdr() {{ print -r -- herdr; return {herdr_rc}; }}")
        if include_tmux:
            definitions.append("function tmux() { print -r -- tmux; return 0; }")

        script = "; ".join(
            (
                *definitions,
                "source shell/zsh/auto_multiplexer.zsh",
                f"auto_start_terminal_multiplexer {str(is_tmux).lower()} {str(is_ide).lower()} {str(is_warp).lower()}",
                "print -r -- rc=$?",
            )
        )
        return run_zsh(script, {"TERM_PROGRAM": "ghostty", **(env_overrides or {})})

    def test_top_level_ghostty_starts_herdr(self):
        result = self.run_auto_start()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["herdr", "rc=10"])

    def test_herdr_failure_keeps_current_shell_without_tmux_fallback(self):
        result = self.run_auto_start(herdr_rc=7)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["herdr", "rc=0"])
        self.assertIn("Herdr exited with status 7", result.stderr)
        self.assertNotIn("tmux", result.stdout)

    def test_missing_herdr_falls_back_to_tmux(self):
        result = self.run_auto_start(herdr_rc=None)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["tmux", "rc=10"])

    def test_nested_and_non_ghostty_shells_do_not_auto_start(self):
        cases = (
            ("herdr", False, False, False, {"HERDR_ENV": "1"}),
            ("tmux", True, False, False, {"TMUX": "/tmp/tmux.sock"}),
            ("ide", False, True, False, {}),
            ("warp", False, False, True, {}),
            ("other terminal", False, False, False, {"TERM_PROGRAM": "Apple_Terminal"}),
        )

        for name, is_tmux, is_ide, is_warp, env_overrides in cases:
            with self.subTest(case=name):
                result = self.run_auto_start(
                    is_tmux=is_tmux,
                    is_ide=is_ide,
                    is_warp=is_warp,
                    env_overrides=env_overrides,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), ["rc=0"])

    def test_managed_shell_stops_only_after_successful_multiplexer_run(self):
        managed = read_text("shell/zsh/managed.zsh")

        self.assertIn('if [[ -n "${TMUX:-}" ]]; then', managed)
        self.assertIn('source "$(dirname "$(realpath "${(%):-%x}")")/auto_multiplexer.zsh"', managed)
        self.assertIn('auto_start_terminal_multiplexer "$IS_TMUX" "$IS_IDE" "$IS_WARP"', managed)
        self.assertIn("if (( auto_multiplexer_rc == 10 )); then", managed)


class HerdrShellToolSelectionTest(unittest.TestCase):
    def test_filter_uses_tmux_wrapper_only_inside_tmux(self):
        cases = (
            ("regular", {}, "fzf"),
            ("herdr", {"HERDR_ENV": "1"}, "fzf"),
            ("tmux", {"TMUX": "/tmp/tmux.sock"}, "fzf-tmux"),
            (
                "herdr inside tmux",
                {"HERDR_ENV": "1", "TMUX": "/tmp/tmux.sock"},
                "fzf",
            ),
        )
        script = "; ".join(
            (
                "function fzf() { return 0; }",
                "function fzf-tmux() { return 0; }",
                "function no_notify() { command \"$@\"; }",
                "source shell/zsh/filter/base.zsh",
                "print -r -- $FILTER_TOOL",
            )
        )

        for name, env_overrides, expected in cases:
            with self.subTest(case=name):
                result = run_zsh(script, env_overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_fzf_tab_uses_popup_only_inside_tmux(self):
        cases = (
            ("regular", {}, "fzf"),
            ("herdr", {"HERDR_ENV": "1"}, "fzf"),
            ("tmux", {"TMUX": "/tmp/tmux.sock"}, "ftb-tmux-popup"),
            (
                "herdr inside tmux",
                {"HERDR_ENV": "1", "TMUX": "/tmp/tmux.sock"},
                "fzf",
            ),
        )
        script = "; ".join(
            (
                "function source_and_zcompile_if_needed() { return 0; }",
                "function znap() { return 0; }",
                "SUBMODULE_DIR=/nonexistent/",
                "source shell/zsh/plugin.zsh",
                "zstyle -s ':fzf-tab:*' fzf-command selected",
                "print -r -- $selected",
            )
        )

        for name, env_overrides, expected in cases:
            with self.subTest(case=name):
                result = run_zsh(script, env_overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)


class HerdrServiceSetupTest(unittest.TestCase):
    def run_setup_herdr_service(
        self,
        *,
        herdr_present: bool = True,
        brew_present: bool = True,
        brew_rc: int = 0,
        uname_output: str = "Darwin",
        service_status: str = "none",
        service_list_ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        definitions = []
        if herdr_present:
            definitions.append("function herdr() { return 0; }")
        if brew_present:
            # services list --json は _herdr_brew_service_status 用の分岐、それ以外は
            # 従来通り呼び出しをエコーして brew_rc を返す。
            if service_list_ok:
                list_body = (
                    'print -r -- \'[{"name":"herdr","status":"' + service_status + '"}]\'; return 0'
                )
            else:
                list_body = "return 1"
            definitions.append(
                "function brew() {\n"
                '  if [[ "$1" == "services" && "$2" == "list" && "$3" == "--json" ]]; then\n'
                f"    {list_body}\n"
                "  fi\n"
                '  print -r -- "brew $*"\n'
                f"  return {brew_rc}\n"
                "}"
            )
        definitions.append(f"function uname() {{ print -r -- {uname_output}; }}")

        script = "; ".join(
            (
                *definitions,
                "source mac/scripts/herdr.sh",
                "setup_herdr_service",
                "print -r -- rc=$?",
            )
        )
        return run_zsh(script)

    def test_darwin_starts_brew_service_when_not_started(self):
        result = self.run_setup_herdr_service(service_status="none")

        self.assertEqual(result.stdout.splitlines(), ["brew services start herdr", "rc=0"])

    def test_darwin_skips_start_when_already_started(self):
        result = self.run_setup_herdr_service(service_status="started")

        self.assertEqual(
            result.stdout.splitlines(),
            ["✓ Herdr brew service already started; skipping start.", "rc=0"],
        )
        # restart/start で稼働中サーバーを落とさないことがこのガードの目的なので、
        # brew services コマンドが(listを除き)一切呼ばれないことを明示的に確認する。
        self.assertNotIn("brew services start herdr", result.stdout)
        self.assertNotIn("brew services restart herdr", result.stdout)

    def test_darwin_starts_brew_service_when_stopped(self):
        result = self.run_setup_herdr_service(service_status="stopped")

        self.assertEqual(result.stdout.splitlines(), ["brew services start herdr", "rc=0"])

    def test_darwin_starts_brew_service_when_absent_from_list(self):
        result = self.run_setup_herdr_service(service_status="", service_list_ok=True)

        self.assertEqual(result.stdout.splitlines(), ["brew services start herdr", "rc=0"])

    def test_darwin_starts_brew_service_when_status_lookup_fails(self):
        # --json 非対応の古い brew や jq 失敗を模したケース。フェイルオープン契約
        # （判定不能なら start する）を検証する。
        result = self.run_setup_herdr_service(service_list_ok=False)

        self.assertEqual(result.stdout.splitlines(), ["brew services start herdr", "rc=0"])

    def test_non_darwin_skips_brew_entirely(self):
        result = self.run_setup_herdr_service(uname_output="Linux")

        self.assertEqual(result.stdout.splitlines(), ["rc=0"])

    def test_missing_herdr_command_fails_before_brew(self):
        result = self.run_setup_herdr_service(herdr_present=False)

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("required command not found: herdr", result.stderr)

    def test_missing_brew_command_fails(self):
        result = self.run_setup_herdr_service(brew_present=False)

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("required command not found: brew", result.stderr)

    def test_brew_failure_propagates_as_nonzero(self):
        result = self.run_setup_herdr_service(brew_rc=1)

        self.assertEqual(result.stdout.splitlines(), ["brew services start herdr", "rc=1"])

    def test_setup_herdr_treats_service_failure_as_best_effort(self):
        # source が本物の setup_herdr_config/integrations/plugins/service を定義するため、
        # モックは source の後で上書きする。
        script = "; ".join(
            (
                "source mac/scripts/herdr.sh",
                "function setup_herdr_config() { return 0; }",
                "function setup_herdr_integrations() { return 0; }",
                "function setup_herdr_plugins() { return 0; }",
                "function setup_herdr_service() { return 1; }",
                'setup_herdr "/tmp/repo" "/tmp/home"',
                "print -r -- rc=$?",
            )
        )
        result = run_zsh(script)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("Warning: failed to start herdr brew service", result.stderr)

    def test_setup_herdr_treats_plugin_failure_as_best_effort(self):
        script = "; ".join(
            (
                "source mac/scripts/herdr.sh",
                "function setup_herdr_config() { return 0; }",
                "function setup_herdr_integrations() { return 0; }",
                "function setup_herdr_plugins() { return 1; }",
                "function setup_herdr_service() { return 0; }",
                'setup_herdr "/tmp/repo" "/tmp/home"',
                "print -r -- rc=$?",
            )
        )
        result = run_zsh(script)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("Warning: failed to link herdr notify-rich plugin", result.stderr)


class HerdrIntegrationsModeTest(unittest.TestCase):
    """install/update モード分離のスキップ判定。実際の staging インストーラ
    (_setup_herdr_integrations_in_staging) は重いので、source 後にセンチネル関数へ
    上書きし、呼ばれたかどうかだけを見る。"""

    def run_setup_herdr_integrations(
        self,
        tmp_path: Path,
        *,
        mode_arg: str = "",
        claude_hook: bool = True,
        codex_hook: bool = True,
        claude_settings: str | None = "registered",
    ) -> subprocess.CompletedProcess[str]:
        home = tmp_path / "home"
        (home / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (home / ".codex").mkdir(parents=True, exist_ok=True)

        if claude_hook:
            (home / ".claude" / "hooks" / "herdr-agent-state.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        if codex_hook:
            (home / ".codex" / "herdr-agent-state.sh").write_text("#!/bin/sh\n", encoding="utf-8")

        if claude_settings == "registered":
            settings = {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "bash ~/.claude/hooks/herdr-agent-state.sh session",
                                }
                            ],
                        }
                    ]
                }
            }
            (home / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        elif claude_settings == "unregistered":
            (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
        elif claude_settings == "malformed":
            (home / ".claude" / "settings.json").write_text("{not json", encoding="utf-8")
        # claude_settings is None のときはファイル自体を作らない(未配備)

        mode_literal = f' "{mode_arg}"' if mode_arg else ""
        script = "; ".join(
            (
                "function herdr() { return 0; }",
                "function trash() { return 0; }",
                "source mac/scripts/herdr.sh",
                "function _setup_herdr_integrations_in_staging() { print -r -- 'staging ran'; return 0; }",
                f'setup_herdr_integrations "" "{home}"{mode_literal}',
                "print -r -- rc=$?",
            )
        )
        return run_zsh(script)

    def test_install_skips_when_fully_deployed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(Path(tmp), mode_arg="install")

        self.assertEqual(
            result.stdout.splitlines(),
            ["✓ Herdr integrations already deployed; skipping installer.", "rc=0"],
        )
        self.assertNotIn("staging ran", result.stdout)

    def test_install_runs_on_fresh_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(
                Path(tmp), mode_arg="install", claude_hook=False, codex_hook=False, claude_settings=None
            )

        self.assertIn("staging ran", result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")

    def test_install_runs_when_codex_hook_missing(self):
        # 部分配備(claudeのみ)を配備済み扱いしない
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(Path(tmp), mode_arg="install", codex_hook=False)

        self.assertIn("staging ran", result.stdout)

    def test_install_runs_when_claude_registration_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(
                Path(tmp), mode_arg="install", claude_settings="unregistered"
            )

        self.assertIn("staging ran", result.stdout)

    def test_install_runs_when_settings_json_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(
                Path(tmp), mode_arg="install", claude_settings="malformed"
            )

        self.assertIn("staging ran", result.stdout)

    def test_update_always_runs_even_when_fully_deployed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(Path(tmp), mode_arg="update")

        self.assertIn("staging ran", result.stdout)

    def test_default_mode_is_update_for_backward_compatibility(self):
        # 既存の6箇所の呼び出し(setup_herdr_integrations repo home)は mode 引数無しで
        # update 相当のまま動く必要がある。
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(Path(tmp), mode_arg="")

        self.assertIn("staging ran", result.stdout)

    def test_invalid_mode_fails_before_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_setup_herdr_integrations(Path(tmp), mode_arg="bogus")

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("expected Herdr integrations mode to be install or update", result.stderr)
        self.assertNotIn("staging ran", result.stdout)

    def test_install_fails_before_skip_check_when_herdr_missing(self):
        # 必須コマンドチェックはスキップ判定より前に残っている。
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            script = "; ".join(
                (
                    "function trash() { return 0; }",
                    "source mac/scripts/herdr.sh",
                    "function _setup_herdr_integrations_in_staging() { print -r -- 'staging ran'; return 0; }",
                    f'setup_herdr_integrations "" "{home}" install',
                    "print -r -- rc=$?",
                )
            )
            result = run_zsh(script)

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("required command not found: herdr", result.stderr)


class SetupHerdrOrchestrationTest(unittest.TestCase):
    def run_setup_herdr(self, mode_arg: str = "") -> subprocess.CompletedProcess[str]:
        mode_literal = f' "{mode_arg}"' if mode_arg else ""
        script = "; ".join(
            (
                "source mac/scripts/herdr.sh",
                "function setup_herdr_config() { print -r -- \"config $*\"; return 0; }",
                "function setup_herdr_integrations() { print -r -- \"integrations $*\"; return 0; }",
                "function setup_herdr_plugins() { print -r -- \"plugins $*\"; return 0; }",
                "function setup_herdr_service() { print -r -- \"service $*\"; return 0; }",
                f'setup_herdr "repo" "home"{mode_literal}',
                "print -r -- rc=$?",
            )
        )
        return run_zsh(script)

    def test_install_mode_forwarded_only_to_integrations(self):
        result = self.run_setup_herdr(mode_arg="install")

        lines = result.stdout.splitlines()
        self.assertIn("integrations repo home install", lines)
        self.assertIn("config repo home", lines)
        self.assertIn("plugins repo", lines)
        self.assertIn("service ", lines)
        self.assertEqual(lines[-1], "rc=0")

    def test_default_mode_is_update(self):
        result = self.run_setup_herdr()

        self.assertIn("integrations repo home update", result.stdout.splitlines())

    def test_invalid_mode_fails_before_any_child_runs(self):
        result = self.run_setup_herdr(mode_arg="bogus")

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("expected Herdr setup mode to be install or update", result.stderr)


class HerdrSetupCallSiteModeTest(unittest.TestCase):
    """mac/initialize と mac/update の呼び出しが install/update を明示していることを
    静的に固定する。これが無いと引数無し呼び出しに戻ってもガードが黙って発火しなくなる。"""

    def test_initialization_entrypoint_uses_install_mode(self):
        script = read_text("mac/initialization/herdr.sh")
        self.assertIn('setup_herdr "" "" install', script)

    def test_update_entrypoint_uses_update_mode(self):
        script = read_text("mac/updates/herdr.sh")
        self.assertIn('setup_herdr "" "" update', script)


class HerdrPluginSetupTest(unittest.TestCase):
    def run_setup_herdr_plugins(
        self,
        *,
        herdr_present: bool = True,
        jq_present: bool = True,
        already_linked: bool = False,
        link_rc: int = 0,
        remote_already_installed: bool = False,
        install_rc: int = 0,
        manifest_present: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        definitions = []
        plugin_ids = []
        if already_linked:
            plugin_ids.append('{"plugin_id":"notify-rich"}')
        if remote_already_installed:
            plugin_ids.append('{"plugin_id":"termscope"}')
        plugins_json = '{"result":{"plugins":[' + ",".join(plugin_ids) + "]}}"
        if herdr_present:
            definitions.append(
                "function herdr() {\n"
                '  if [[ "$1" == "plugin" && "$2" == "list" ]]; then\n'
                f"    print -r -- '{plugins_json}'\n"
                "    return 0\n"
                '  elif [[ "$1" == "plugin" && "$2" == "link" ]]; then\n'
                '    print -r -- "plugin link $3"\n'
                f"    return {link_rc}\n"
                '  elif [[ "$1" == "plugin" && "$2" == "install" ]]; then\n'
                '    print -r -- "plugin install $3"\n'
                f"    return {install_rc}\n"
                "  fi\n"
                "}"
            )
        repo_root = REPO_ROOT if manifest_present else "/tmp/settingfiles-plugin-manifest-missing"

        script = "; ".join(
            (
                *definitions,
                "source mac/scripts/herdr.sh",
                f'setup_herdr_plugins "{repo_root}"',
                "print -r -- rc=$?",
            )
        )
        if jq_present:
            return run_zsh(script)
        # jq自体はシステムPATH上の実体(/usr/bin/jq)なので関数モックでは隠せない。
        # 「jqが無い」環境を再現するため、jqを含まない空ディレクトリだけのPATHを渡す。
        return run_zsh(script, {"PATH": "/nonexistent-empty-bin"})

    def test_links_plugin_when_not_yet_registered(self):
        result = self.run_setup_herdr_plugins(already_linked=False)

        self.assertIn(
            f"plugin link {REPO_ROOT}/terminal/herdr/plugins/notify-rich",
            result.stdout,
        )
        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")

    def test_installs_declared_remote_plugin_when_not_yet_registered(self):
        result = self.run_setup_herdr_plugins(
            already_linked=True, remote_already_installed=False
        )

        self.assertIn("plugin install iurysza/termscope", result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")

    def test_skips_remote_plugin_install_when_already_registered(self):
        result = self.run_setup_herdr_plugins(
            already_linked=True, remote_already_installed=True
        )

        self.assertNotIn("plugin install", result.stdout)
        self.assertIn("✓ Herdr plugin already installed: termscope", result.stdout)

    def test_remote_plugin_install_failure_propagates_as_nonzero(self):
        result = self.run_setup_herdr_plugins(
            already_linked=True, install_rc=1
        )

        self.assertEqual(result.stdout.splitlines()[-1], "rc=1")

    def test_skips_link_when_already_registered(self):
        result = self.run_setup_herdr_plugins(
            already_linked=True, remote_already_installed=True
        )

        self.assertEqual(
            result.stdout.splitlines(),
            [
                "✓ Herdr plugin already linked: notify-rich",
                "✓ Herdr plugin already installed: termscope",
                "rc=0",
            ],
        )

    def test_link_failure_propagates_as_nonzero(self):
        result = self.run_setup_herdr_plugins(already_linked=False, link_rc=1)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=1")

    def test_missing_manifest_fails_before_calling_herdr(self):
        result = self.run_setup_herdr_plugins(manifest_present=False)

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("managed Herdr plugin manifest is unavailable", result.stderr)

    def test_missing_herdr_command_fails(self):
        result = self.run_setup_herdr_plugins(herdr_present=False)

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("required command not found: herdr", result.stderr)

    def test_missing_jq_command_fails(self):
        result = self.run_setup_herdr_plugins(jq_present=False)

        self.assertEqual(result.stdout.splitlines(), ["rc=1"])
        self.assertIn("required command not found: jq", result.stderr)


if __name__ == "__main__":
    unittest.main()
