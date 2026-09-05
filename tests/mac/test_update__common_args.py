import subprocess
import unittest
from pathlib import Path


from support import REPO_ROOT

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

ENTRY_SCRIPTS = (
    ("mac/update", "smart_merge_json"),
    ("mac/initialization/initialize", "enable_sudo_bell"),
)


class CommonArgsWiringTest(unittest.TestCase):
    """mac/initialize と mac/update の共通引数パースの配線を検証する。

    正常系で通しの実行はできない（brew/npm/pipx を叩く）ため、配線の順序は
    ソース文字列で検証する。未知引数のケースだけはパーサで即座に終了し
    副作用が始まらないので、実プロセスを起動して確かめる。
    """

    def test_mac_initialize_forwards_arguments(self):
        text = (REPO_ROOT / "mac/initialize").read_text(encoding="utf-8")

        self.assertIn('"$@"', text)

    def test_entry_scripts_parse_args_before_any_side_effect(self):
        for script_path, first_effect in ENTRY_SCRIPTS:
            with self.subTest(script=script_path):
                text = (REPO_ROOT / script_path).read_text(encoding="utf-8")

                self.assertIn("parse_settingfiles_common_args", text)

                source_index = text.index("scripts/common.sh")
                parse_index = text.index("parse_settingfiles_common_args")
                effect_index = text.index(first_effect)

                # common.sh を読んだ後でなければ関数が未定義になる
                self.assertLess(source_index, parse_index, script_path)
                # 最初の実処理より前で落ちなければ副作用が始まってしまう
                self.assertLess(parse_index, effect_index, script_path)

    def test_entry_scripts_abort_on_unknown_option_without_side_effects(self):
        for script_path, _ in (("mac/update", None), ("mac/initialize", None)):
            with self.subTest(script=script_path):
                result = subprocess.run(
                    [str(REPO_ROOT / script_path), "--bogus"],
                    cwd=REPO_ROOT,
                    env={
                        "HOME": str(REPO_ROOT),
                        "PATH": SYSTEM_PATH,
                        "LANG": "en_US.UTF-8",
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                )
                output = result.stdout + result.stderr

                self.assertEqual(result.returncode, 2, output)
                self.assertIn("Unknown option: --bogus", result.stderr)
                # brew や submodule 更新に到達していないこと
                self.assertNotIn("start brew update.", output)
                self.assertNotIn("start git submodule setting.", output)
                self.assertNotIn("Starting macOS initialization...", output)

    def test_entry_scripts_print_usage_for_help(self):
        for script_path in ("mac/update", "mac/initialize"):
            with self.subTest(script=script_path):
                result = subprocess.run(
                    [str(REPO_ROOT / script_path), "--help"],
                    cwd=REPO_ROOT,
                    env={
                        "HOME": str(REPO_ROOT),
                        "PATH": SYSTEM_PATH,
                        "LANG": "en_US.UTF-8",
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                )
                output = result.stdout + result.stderr

                self.assertEqual(result.returncode, 0, output)
                self.assertIn("--reprompt-reviewed", result.stdout)
                self.assertIn("--no-reprompt-reviewed", result.stdout)
                self.assertNotIn("start brew update.", output)


if __name__ == "__main__":
    unittest.main()
