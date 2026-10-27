import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

BASE_BREWFILE = 'brew "git"\nvscode "aaa.first"\nvscode "zzz.last"\nmas "Xcode", id: 497799835\n'


class SyncVscodeExtensionsTest(unittest.TestCase):
    """sync_enabled_vscode_extensions_to_brewfile: 未記載の有効拡張を1件ずつ確認して Brewfile へ反映する。

    先に全候補を一覧表示し、a/n/s/i で一括選択、i なら各候補に y/n/s/a/q を聞く。
    n は ignore ファイルに記録して次回以降聞かない。
    入力の不正・EOF では勝手に追加しない(fail-safe)。
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="settingfiles-vscode-sync-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        state_db = self.home / "Library/Application Support/Code/User/globalStorage/state.vscdb"
        state_db.parent.mkdir(parents=True)
        state_db.write_text("", encoding="utf-8")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.brewfile = self.tmp / "Brewfile"
        self.ignore_file = self.tmp / "state" / "ignored.txt"

    def write_stub(self, name: str, body: str):
        path = self.bin / name
        path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        path.chmod(0o755)

    def run_sync(
        self,
        *,
        stdin: str,
        installed: list[str],
        disabled: list[str] | None = None,
        brewfile: str = BASE_BREWFILE,
        ignored: list[str] | None = None,
        reprompt: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required for this test")
        self.brewfile.write_text(brewfile, encoding="utf-8")
        if ignored is not None:
            self.ignore_file.parent.mkdir(parents=True, exist_ok=True)
            self.ignore_file.write_text("".join(f"{i}\n" for i in ignored), encoding="utf-8")

        self.write_stub("code", "cat <<'EOF'\n" + "\n".join(installed) + "\nEOF")
        disabled_json = "" if not disabled else '[{"id":"' + '"},{"id":"'.join(disabled) + '"}]'
        self.write_stub("sqlite3", f"printf '%s' '{disabled_json}'")

        overrides = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin:{Path(node).parent}",
            "SETTINGFILES_VSCODE_EXTENSION_IGNORE_FILE": str(self.ignore_file),
        }
        if reprompt:
            overrides["SETTINGFILES_DIFF_REVIEW_REPROMPT"] = "1"
        script = (
            f'source "{REPO_ROOT}/mac/scripts/common.sh"\n'
            "_start_prompt_wait_notification() { :; }\n"
            "_finish_prompt_wait_notification() { :; }\n"
            'sync_enabled_vscode_extensions_to_brewfile "$1"\n'
        )
        return subprocess.run(
            ["/bin/zsh", "-f", "-c", script, "zsh", str(self.brewfile)],
            input=stdin,
            env=sanitized_env(overrides),
            text=True,
            capture_output=True,
            check=False,
        )

    def brewfile_text(self) -> str:
        return self.brewfile.read_text(encoding="utf-8")

    def ignored_ids(self) -> list[str]:
        if not self.ignore_file.exists():
            return []
        return self.ignore_file.read_text(encoding="utf-8").split()

    def test_candidates_listed_before_first_prompt(self):
        result = self.run_sync(stdin="s\n", installed=["bbb.second", "ccc.third"])

        self.assertEqual(result.returncode, 0, result.stderr)
        first_prompt = result.stdout.index("[a]全部追加")
        self.assertLess(result.stdout.index("bbb.second"), first_prompt)
        self.assertLess(result.stdout.index("ccc.third"), first_prompt)
        self.assertEqual(self.brewfile_text(), BASE_BREWFILE)
        self.assertEqual(self.ignored_ids(), [])

    def test_bulk_add_all(self):
        result = self.run_sync(stdin="a\n", installed=["bbb.second", "ccc.third"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('vscode "bbb.second"', self.brewfile_text())
        self.assertIn('vscode "ccc.third"', self.brewfile_text())
        self.assertEqual(self.ignored_ids(), [])

    def test_bulk_ignore_all_records_every_candidate(self):
        result = self.run_sync(stdin="n\n", installed=["bbb.second", "ccc.third"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.brewfile_text(), BASE_BREWFILE)
        self.assertEqual(self.ignored_ids(), ["bbb.second", "ccc.third"])

    def test_bulk_invalid_input_asks_again(self):
        result = self.run_sync(stdin="\nx\na\n", installed=["bbb.second"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("a / n / s / i", result.stdout)
        self.assertIn('vscode "bbb.second"', self.brewfile_text())

    def test_enter_after_each_answer_does_not_redisplay_candidate(self):
        # 回帰: 1文字読みだと Enter の改行が次の候補への不正入力になり二重表示されていた。
        result = self.run_sync(stdin="i\nn\ny\n", installed=["bbb.second", "ccc.third"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("y / n / s / a / q", result.stdout)
        self.assertEqual(result.stdout.count("[1/2]"), 1)
        self.assertEqual(result.stdout.count("[2/2]"), 1)
        self.assertEqual(self.ignored_ids(), ["bbb.second"])
        self.assertIn('vscode "ccc.third"', self.brewfile_text())
        self.assertNotIn('vscode "bbb.second"', self.brewfile_text())

    def test_per_item_choices_add_ignore_and_skip(self):
        result = self.run_sync(stdin="i\ny\nn\ns\n", installed=["bbb.second", "ccc.third", "ddd.fourth"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.brewfile_text(),
            'brew "git"\nvscode "aaa.first"\nvscode "bbb.second"\nvscode "zzz.last"\nmas "Xcode", id: 497799835\n',
        )
        self.assertEqual(self.ignored_ids(), ["ccc.third"])

    def test_ignored_ids_are_not_asked_again(self):
        result = self.run_sync(stdin="", installed=["bbb.second"], ignored=["bbb.second"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.brewfile_text(), BASE_BREWFILE)
        self.assertIn("already contains", result.stdout)
        self.assertNotIn("bbb.second", result.stdout)

    def test_add_all_adds_remaining_candidates(self):
        result = self.run_sync(stdin="i\na\n", installed=["bbb.second", "ccc.third", "ddd.fourth"])

        self.assertEqual(result.returncode, 0, result.stderr)
        for extension in ("bbb.second", "ccc.third", "ddd.fourth"):
            self.assertIn(f'vscode "{extension}"', self.brewfile_text())

    def test_quit_skips_remaining_without_recording(self):
        result = self.run_sync(stdin="i\nq\n", installed=["bbb.second", "ccc.third"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.brewfile_text(), BASE_BREWFILE)
        self.assertEqual(self.ignored_ids(), [])

    def test_invalid_key_asks_again_then_accepts_valid_key(self):
        result = self.run_sync(stdin="i\n\ny\n", installed=["bbb.second"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("y / n / s / a / q", result.stdout)
        self.assertIn('vscode "bbb.second"', self.brewfile_text())

    def test_eof_never_adds_anything(self):
        # 入力が尽きた場合に勝手に追加しないことを固定する(fail-safe)。
        result = self.run_sync(stdin="", installed=["bbb.second"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.brewfile_text(), BASE_BREWFILE)
        self.assertEqual(self.ignored_ids(), [])

    def test_reprompt_flag_asks_ignored_ids_again(self):
        result = self.run_sync(stdin="i\ny\n", installed=["bbb.second"], ignored=["bbb.second"], reprompt=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('vscode "bbb.second"', self.brewfile_text())

    def test_disabled_and_existing_extensions_are_not_candidates(self):
        result = self.run_sync(
            stdin="",
            installed=["AAA.First", "bbb.disabled"],
            disabled=["bbb.disabled"],
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.brewfile_text(), BASE_BREWFILE)
        self.assertIn("already contains", result.stdout)

    def test_no_candidates_does_not_prompt(self):
        result = self.run_sync(stdin="", installed=["aaa.first"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already contains", result.stdout)
        self.assertNotIn("[y]", result.stdout)

    def test_output_has_no_ansi_escape_when_not_a_tty(self):
        result = self.run_sync(stdin="a\n", installed=["bbb.second"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b[", result.stdout)


if __name__ == "__main__":
    unittest.main()
