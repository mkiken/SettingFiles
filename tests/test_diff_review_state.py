import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def quote(path: Path) -> str:
    return shlex.quote(str(path))


class ZshSession:
    def __init__(self, root: Path):
        self.root = root
        self.home = root / "home"
        self.state_dir = root / "state"
        self.home.mkdir()

    def run(
        self,
        script: str,
        input_text: str = "",
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            "HOME": str(self.home),
            "SET": f"{REPO_ROOT}/",
            "PATH": SYSTEM_PATH,
            "DISABLE_NOTIFY": "1",
            "SETTINGFILES_DIFF_REVIEW_DIR": str(self.state_dir),
            "LANG": "en_US.UTF-8",
        }
        if extra_env:
            env.update(extra_env)

        return subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


class DiffReviewStateTest(unittest.TestCase):
    def test_smart_copy_repeated_same_diff_shows_skip_first_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.txt"
            dst = Path(tmpdir) / "dst.txt"
            src.write_text("new\n", encoding="utf-8")
            dst.write_text("old\n", encoding="utf-8")

            result = session.run(
                (
                    "source shell/zsh/alias/utils.zsh; "
                    f"smart_copy {quote(src)} {quote(dst)}; "
                    f"smart_copy {quote(src)} {quote(dst)}"
                ),
                "s\ns\n",
            )

            output = combined_output(result)
            self.assertEqual(result.returncode, 0, output)
            self.assertEqual(dst.read_text(encoding="utf-8"), "old\n")
            self.assertEqual(output.count("=== Differences found ==="), 1)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn("[s]kip / [v]iew diff / [o]verwrite (default: s):", output)
            self.assertEqual(len(list(session.state_dir.glob("*.state"))), 1)

    def test_smart_copy_repeated_view_shows_diff_and_existing_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.txt"
            dst = Path(tmpdir) / "dst.txt"
            src.write_text("new\n", encoding="utf-8")
            dst.write_text("old\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; smart_copy {quote(src)} {quote(dst)}"

            seed = session.run(script, "s\n")
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "v\ns\n")
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn("=== Differences found ===", output)
            self.assertIn("Overwrite? [o]verwrite / [s]kip (default: s):", output)
            self.assertEqual(dst.read_text(encoding="utf-8"), "old\n")

    def test_smart_copy_binary_signature_changes_when_bytes_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.bin"
            dst = Path(tmpdir) / "dst.bin"
            src.write_bytes(b"\x00new-one\n")
            dst.write_bytes(b"\x00old\n")
            script = f"source shell/zsh/alias/utils.zsh; smart_copy {quote(src)} {quote(dst)}"

            seed = session.run(script, "s\n")
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            src.write_bytes(b"\x00new-two\n")
            result = session.run(script, "s\n")
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn("前回確認時と同じ差分です:", output)
            self.assertIn("=== Differences found ===", output)
            self.assertEqual(dst.read_bytes(), b"\x00old\n")

    @unittest.skipIf(shutil.which("jq", path=SYSTEM_PATH) is None, "jq is required")
    def test_smart_merge_action_bypasses_repeated_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text('{"a":2,"b":1}\n', encoding="utf-8")
            dst.write_text('{"a":1,"c":3}\n', encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; smart_merge_json {quote(src)} {quote(dst)} src dst"

            seed = session.run(script, "k\n")
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, extra_env={"SMART_MERGE_ACTION": "keep"})
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn("前回確認時と同じ差分です:", output)
            self.assertIn("=== Differences found ===", output)
            self.assertIn("Skipped: dst", output)

    @unittest.skipIf(shutil.which("jq", path=SYSTEM_PATH) is None, "jq is required")
    def test_smart_merge_json_repeated_prompt_keeps_merge_choices(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text('{"a":2,"b":1}\n', encoding="utf-8")
            dst.write_text('{"a":1,"c":3}\n', encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; smart_merge_json {quote(src)} {quote(dst)} src dst"

            seed = session.run(script, "k\n")
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "k\n")
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn("[k]eep / [v]iew diff / [o]verwrite", output)
            self.assertIn("[m]erge source priority", output)
            self.assertIn("[d]merge destination priority", output)
            self.assertNotIn("=== Differences found ===", output)

    @unittest.skipIf(shutil.which("jq", path=SYSTEM_PATH) is None, "jq is required")
    def test_smart_merge_json_removes_tmpdir_json_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            temp_dir = Path(tmpdir) / "tmp"
            temp_dir.mkdir()
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text('{"a":2,"b":1}\n', encoding="utf-8")
            dst.write_text('{"a":1,"c":3}\n', encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; smart_merge_json {quote(src)} {quote(dst)} src dst"

            result = session.run(script, "k\n", extra_env={"TMPDIR": f"{temp_dir}/"})
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertEqual(list(temp_dir.iterdir()), [])

    def test_make_symlink_repeated_conflict_shows_skip_first_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.write_text("source\n", encoding="utf-8")
            dst.write_text("existing\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}"

            seed = session.run(script, "n\n")
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "s\n")
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn("[s]kip / [v]iew change / [o]verwrite (default: s):", output)
            self.assertFalse(dst.is_symlink())
            self.assertEqual(dst.read_text(encoding="utf-8"), "existing\n")

    def test_make_symlink_repeated_view_shows_change_summary_and_confirm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.write_text("source\n", encoding="utf-8")
            dst.write_text("existing\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}"

            seed = session.run(script, "n\n")
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "v\nn\n")
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn(f"Existing path: {dst}", output)
            self.assertIn("Existing type: file", output)
            self.assertIn(f"Intended symlink: {dst} -> {src}", output)
            self.assertIn("シンボリックリンクではない既存パスがあります:", output)
            self.assertFalse(dst.is_symlink())
            self.assertEqual(dst.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
