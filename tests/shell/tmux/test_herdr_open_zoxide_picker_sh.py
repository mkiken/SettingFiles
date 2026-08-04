"""Herdr zoxide picker ランチャーの環境復元テスト。"""
import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from support import REPO_ROOT

LAUNCHER_SCRIPT = REPO_ROOT / "shell/tmux/herdr-open-zoxide-picker.sh"
HERDR_CONFIG = REPO_ROOT / "terminal/herdr/config.toml"

PLUGIN_ID = "herdr-zoxide"


class HerdrZoxidePickerLauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.picker_log = self.root / "picker.log"

        # インストール先はハッシュ付きディレクトリなので、テストでも同じ形を再現する。
        self.plugin_root = self.root / "plugins" / "github" / "herdr-zoxide-deadbeef"
        self.plugin_root.mkdir(parents=True)
        self.config_dir = self.root / "plugins" / "config" / PLUGIN_ID
        self.config_dir.mkdir(parents=True)

        self._write_picker()
        self._write_fake_herdr(plugin_root=str(self.plugin_root), config_dir_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_picker(self):
        picker = self.plugin_root / "zoxide-picker.sh"
        picker.write_text(
            """#!/bin/bash
set -euo pipefail
{
  printf 'config_dir=%s\\n' "$HERDR_PLUGIN_CONFIG_DIR"
  printf 'lang=%s\\n' "${LANG:-<unset>}"
  printf 'args=%s\\n' "$*"
} > "$HERDR_TEST_PICKER_LOG"
""",
            encoding="utf-8",
        )
        picker.chmod(0o755)

    def _write_fake_herdr(self, plugin_root, config_dir_ok):
        if plugin_root is None:
            listing = {"result": {"plugins": []}}
        else:
            listing = {
                "result": {
                    "plugins": [{"plugin_id": PLUGIN_ID, "plugin_root": plugin_root}]
                }
            }
        config_dir_branch = (
            f'printf \'%s\\n\' "{self.config_dir}"' if config_dir_ok else "exit 1"
        )
        script = f"""#!/bin/bash
case "$1 $2" in
  "plugin list")
    cat <<'JSON'
{json.dumps(listing)}
JSON
    ;;
  "plugin config-dir")
    {config_dir_branch}
    ;;
esac
"""
        path = self.fake_bin / "herdr"
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)

    def _env(self, **extra):
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fake_bin}{os.pathsep}{env['PATH']}",
                "HERDR_BIN_PATH": str(self.fake_bin / "herdr"),
                "HERDR_TEST_PICKER_LOG": str(self.picker_log),
                "HOME": str(self.home),
            }
        )
        env.update(extra)
        return env

    def _run(self, *args, env=None):
        return subprocess.run(
            ["bash", str(LAUNCHER_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env if env is not None else self._env(),
        )

    def _picker_fields(self):
        return dict(
            line.split("=", 1)
            for line in self.picker_log.read_text(encoding="utf-8").splitlines()
        )

    def test_launcher_starts_upstream_picker(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.picker_log.exists())

    def test_plugin_config_dir_is_exported(self):
        self._run()

        self.assertEqual(self._picker_fields()["config_dir"], str(self.config_dir))

    def test_config_dir_failure_falls_back_to_home(self):
        self._write_fake_herdr(plugin_root=str(self.plugin_root), config_dir_ok=False)

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._picker_fields()["config_dir"],
            str(self.home / ".config/herdr/plugins/config/herdr-zoxide"),
        )

    def test_missing_lang_gets_utf8_fallback(self):
        env = self._env()
        env.pop("LANG", None)

        self._run(env=env)

        self.assertEqual(self._picker_fields()["lang"], "en_US.UTF-8")

    def test_existing_lang_is_preserved(self):
        self._run(env=self._env(LANG="ja_JP.UTF-8"))

        self.assertEqual(self._picker_fields()["lang"], "ja_JP.UTF-8")

    def test_uninstalled_plugin_does_not_start_picker(self):
        self._write_fake_herdr(plugin_root=None, config_dir_ok=True)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not installed", result.stderr)
        # プラグイン未インストール時に無言で閉じると原因が追えないため、起動しないことを固定する。
        self.assertFalse(self.picker_log.exists())

    def test_missing_picker_file_does_not_start_picker(self):
        (self.plugin_root / "zoxide-picker.sh").unlink()

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unavailable", result.stderr)
        self.assertFalse(self.picker_log.exists())

    def test_arguments_pass_through_to_picker(self):
        self._run("--depth", "3")

        self.assertEqual(self._picker_fields()["args"], "--depth 3")


class HerdrZoxideKeyBindingTest(unittest.TestCase):
    """prefix+shift+o が PATH を復元するログインシェル経由であることを固定する。"""

    def setUp(self):
        with HERDR_CONFIG.open("rb") as handle:
            config = tomllib.load(handle)
        self.binding = next(
            entry
            for entry in config["keys"]["command"]
            if entry["key"] == "prefix+shift+o"
        )

    def test_binding_uses_login_shell(self):
        # 非ログインの `zsh -ic` では Homebrew が PATH に載らず managed.zsh の
        # `brew --prefix` も失敗するため、picker が再び zoxide を見失う。
        self.assertIn("zsh -ilc", self.binding["command"])
        self.assertNotIn("zsh -ic", self.binding["command"])

    def test_binding_sets_popup_command_guard(self):
        # HERDR_POPUP_COMMAND=1 が無いと Powerlevel10k の gitstatus 初期化が
        # popup PTY に弾かれ、zsh -ilc の子プロセスが即終了する。
        self.assertIn("HERDR_POPUP_COMMAND=1", self.binding["command"])

    def test_binding_invokes_the_managed_launcher(self):
        self.assertIn("herdr-open-zoxide-picker.sh", self.binding["command"])


if __name__ == "__main__":
    unittest.main()
