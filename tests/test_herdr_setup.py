import os
import subprocess
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
        self.assertEqual(config["ui"]["toast"], {"delivery": "system", "delay_seconds": 1})
        self.assertFalse(config["ui"]["sound"]["enabled"])
        self.assertTrue(config["session"]["resume_agents_on_restore"])
        self.assertFalse(config["experimental"]["pane_history"])

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_managed_config_maps_basic_tmux_style_keys(self):
        keys = tomllib.loads(read_text("terminal/herdr/config.toml"))["keys"]
        expected = {
            "prefix": "ctrl+t",
            "new_tab": "prefix+c",
            "previous_tab": "prefix+p",
            "next_tab": "prefix+n",
            "focus_pane_left": "prefix+h",
            "focus_pane_down": "prefix+j",
            "focus_pane_up": "prefix+k",
            "focus_pane_right": "prefix+l",
            "split_vertical": "prefix+v",
            "split_horizontal": "prefix+minus",
            "close_pane": "prefix+x",
            "copy_mode": "prefix+[",
            "detach": "prefix+q",
            "reload_config": "prefix+shift+r",
        }

        self.assertEqual(keys, expected)

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


if __name__ == "__main__":
    unittest.main()
