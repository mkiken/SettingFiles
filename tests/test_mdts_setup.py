import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

# mdts's saveConfig() always rewrites the full object (never a partial merge), so the
# repo copy is a faithful, complete representation. If mdts ever adds a key, this set
# must be updated deliberately -- otherwise a stale key set silently hides what mdts
# would drop on its next write.
SUPPORTED_CONFIG_KEYS = {
    "fontFamily",
    "fontFamilyMonospace",
    "fontSize",
    "theme",
    "syntaxHighlighterTheme",
    "enableBreaks",
}


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


class MdtsConfigSourceTest(unittest.TestCase):
    def test_repo_config_is_valid_json_with_exactly_the_supported_keys(self):
        config = json.loads(read_text("terminal/mdts/config.json"))

        self.assertEqual(set(config.keys()), SUPPORTED_CONFIG_KEYS)

    def test_no_hardcoded_personal_paths(self):
        for relative_path in ("terminal/mdts/config.json", "terminal/mdts/mdts-plans.user.css", "mac/scripts/mdts.sh"):
            with self.subTest(path=relative_path):
                self.assertNotIn("/Users/", read_text(relative_path))


class MdtsUserStyleTest(unittest.TestCase):
    def setUp(self):
        self.css = read_text("terminal/mdts/mdts-plans.user.css")

    def test_inline_code_selector_excludes_pre(self):
        # A bare `code { color: ... !important }` would flatten every syntax-
        # highlighted token to one color; only :not(pre) > code is safe.
        self.assertIn(":not(pre) > code", self.css)

    def test_no_rule_sets_color_on_a_pre_descendant_selector(self):
        for line in self.css.splitlines():
            if "pre" in line and "code" in line and ":not(pre)" not in line:
                self.fail(f"a pre-descendant selector must not set color: {line!r}")

    def test_all_heading_levels_present_in_both_light_and_dark_blocks(self):
        # Upstream itself omits h6, so a copy-paste dropping a level in one of the
        # two color blocks is the most likely authoring mistake here.
        light_block, dark_block = self.css.split('body[data-theme="dark"]', 1)
        for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
            with self.subTest(level=level, block="light"):
                self.assertIn(f".markdown-body {level} ", light_block)
            with self.subTest(level=level, block="dark"):
                self.assertIn(f".markdown-body {level} ", dark_block)

    def test_scoped_to_localhost_domains_only(self):
        self.assertIn('domain("localhost")', self.css)
        self.assertIn('domain("127.0.0.1")', self.css)


class MdtsSetupGuardTest(unittest.TestCase):
    def run_setup_mdts_config(self, home: Path, *, repo_root: str | None = None) -> subprocess.CompletedProcess[str]:
        root = repo_root if repo_root is not None else f"{REPO_ROOT}/"
        script = "; ".join(
            (
                'source shell/zsh/alias/utils.zsh',
                "source mac/scripts/mdts.sh",
                f'setup_mdts_config "{root}" "{home}"',
                "print -r -- rc=$?",
            )
        )
        return run_zsh(script)

    def test_fresh_home_creates_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            result = self.run_setup_mdts_config(home)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=0", result.stderr)
            live_config = home / ".config/mdts/config.json"
            self.assertTrue(live_config.is_symlink())
            self.assertEqual(
                os.readlink(live_config),
                str(REPO_ROOT / "terminal/mdts/config.json"),
            )

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            self.run_setup_mdts_config(home)
            live_config = home / ".config/mdts/config.json"
            mtime_before = live_config.lstat().st_mtime_ns

            result = self.run_setup_mdts_config(home)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=0", result.stderr)
            self.assertIn("✓ Already linked", result.stdout)
            self.assertEqual(live_config.lstat().st_mtime_ns, mtime_before)

    def test_symlink_to_a_different_target_errors_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            live_config = home / ".config/mdts/config.json"
            live_config.parent.mkdir(parents=True)
            foreign_target = home / "foreign-config.json"
            foreign_target.write_text('{"foreign": true}', encoding="utf-8")
            live_config.symlink_to(foreign_target)

            result = self.run_setup_mdts_config(home)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=1")
            self.assertIn("unexpected symlink target", result.stderr)
            self.assertEqual(os.readlink(live_config), str(foreign_target))

    def test_existing_regular_file_errors_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            live_config = home / ".config/mdts/config.json"
            live_config.parent.mkdir(parents=True)
            live_config.write_text('{"pre-existing": true}', encoding="utf-8")

            result = self.run_setup_mdts_config(home)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=1")
            self.assertIn("refusing to replace", result.stderr)
            self.assertFalse(live_config.is_symlink())
            self.assertEqual(live_config.read_text(encoding="utf-8"), '{"pre-existing": true}')

    def test_missing_source_errors_without_creating_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            missing_repo_root = "/tmp/settingfiles-mdts-missing-repo/"

            result = self.run_setup_mdts_config(home, repo_root=missing_repo_root)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=1")
            self.assertIn("managed mdts config is unavailable", result.stderr)
            self.assertFalse((home / ".config/mdts").exists())

    def test_missing_parent_directory_is_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            self.assertFalse((home / ".config").exists())

            result = self.run_setup_mdts_config(home)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=0", result.stderr)
            self.assertTrue((home / ".config/mdts/config.json").is_symlink())

    def test_repo_root_trailing_slash_does_not_affect_the_link_target(self):
        # mac/update passes $Repo, which always has a trailing slash (see
        # mac/scripts/common.sh); a test or caller might reasonably omit it.
        # ${repo_root%/} must make both forms resolve to the identical link target,
        # or make_symlink's literal readlink comparison never reports "Already
        # linked" and the link churns on every run.
        with_slash = f"{REPO_ROOT}/"
        without_slash = str(REPO_ROOT)

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            self.run_setup_mdts_config(home, repo_root=with_slash)
            first_target = os.readlink(home / ".config/mdts/config.json")

            result = self.run_setup_mdts_config(home, repo_root=without_slash)
            second_target = os.readlink(home / ".config/mdts/config.json")

            self.assertEqual(result.stdout.splitlines()[-1], "rc=0", result.stderr)
            self.assertIn("✓ Already linked", result.stdout)
            self.assertEqual(first_target, second_target)

    def test_target_home_containing_a_space_is_handled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home with space"
            home.mkdir()

            result = self.run_setup_mdts_config(home)

            self.assertEqual(result.stdout.splitlines()[-1], "rc=0", result.stderr)
            self.assertTrue((home / ".config/mdts/config.json").is_symlink())


class MdtsSetupComposesConfigTest(unittest.TestCase):
    def test_setup_mdts_propagates_config_failure(self):
        script = "; ".join(
            (
                "source mac/scripts/mdts.sh",
                "function setup_mdts_config() { return 1; }",
                'setup_mdts "/tmp/repo" "/tmp/home"',
                "print -r -- rc=$?",
            )
        )
        result = run_zsh(script)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=1")

    def test_setup_mdts_succeeds_when_config_succeeds(self):
        script = "; ".join(
            (
                "source mac/scripts/mdts.sh",
                "function setup_mdts_config() { return 0; }",
                'setup_mdts "/tmp/repo" "/tmp/home"',
                "print -r -- rc=$?",
            )
        )
        result = run_zsh(script)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")


class MdtsWiringTest(unittest.TestCase):
    def test_updates_script_sources_common_then_mdts_scripts_then_calls_setup(self):
        content = read_text("mac/updates/mdts.sh")

        common_index = content.index('source "$(dirname "$0")/../scripts/common.sh"')
        scripts_index = content.index('source "${Repo}mac/scripts/mdts.sh"')
        call_index = content.index("setup_mdts")

        self.assertLess(common_index, scripts_index)
        self.assertLess(scripts_index, call_index)

    def test_mac_update_sources_mdts_update_script(self):
        update = read_text("mac/update")

        self.assertEqual(update.count('source "$(dirname "$0")/updates/mdts.sh"'), 1)
        self.assertGreater(
            update.index('source "$(dirname "$0")/updates/mdts.sh"'),
            update.index('source "$(dirname "$0")/updates/herdr.sh"'),
        )

    def test_dev_tools_calls_setup_mdts_after_installing_mdts(self):
        dev_tools = read_text("mac/initialization/dev_tools.sh")

        self.assertIn("homebrew_npm install -g mdts", dev_tools)
        self.assertGreater(
            dev_tools.index("setup_mdts"),
            dev_tools.index("homebrew_npm install -g mdts"),
        )


if __name__ == "__main__":
    unittest.main()
