import json
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
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
        reprompt: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            "HOME": str(self.home),
            "SET": f"{REPO_ROOT}/",
            "PATH": SYSTEM_PATH,
            "DISABLE_NOTIFY": "1",
            "SETTINGFILES_DIFF_REVIEW_DIR": str(self.state_dir),
            "LANG": "en_US.UTF-8",
        }
        # 既定では署名一致時に自動スキップするため、反復プロンプトを検証する
        # テストは reprompt=True で明示的に有効化する。
        if reprompt:
            env["SETTINGFILES_DIFF_REVIEW_REPROMPT"] = "1"
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
    def test_diff_review_reprompt_enabled_only_accepts_truthy_values(self):
        truthy = ["1", "true", "TRUE", "True", "yes", "YES", "Yes", "on", "ON"]
        falsy = ["", "0", "false", "no", "off", "foo"]

        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            script = (
                "source shell/zsh/alias/utils.zsh; "
                "_diff_review_reprompt_enabled"
            )

            for value in truthy:
                result = session.run(
                    script,
                    extra_env={"SETTINGFILES_DIFF_REVIEW_REPROMPT": value},
                )
                self.assertEqual(
                    result.returncode, 0, f"{value!r}: {combined_output(result)}"
                )

            for value in falsy:
                result = session.run(
                    script,
                    extra_env={"SETTINGFILES_DIFF_REVIEW_REPROMPT": value},
                )
                self.assertEqual(
                    result.returncode, 1, f"{value!r}: {combined_output(result)}"
                )

            # 未設定も自動スキップ側（デフォルト）に落ちる
            result = session.run(script)
            self.assertEqual(result.returncode, 1, combined_output(result))

    def test_smart_copy_repeated_same_diff_auto_skips_by_default(self):
        """署名一致時、既定では反復プロンプトを出さず自動スキップする。"""
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
                "s\n",
            )
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertEqual(dst.read_text(encoding="utf-8"), "old\n")
            self.assertEqual(output.count("=== Differences found ==="), 1, output)
            self.assertNotIn("前回確認時と同じ差分です: \n", output)
            self.assertNotIn("[s]kip / [v]iew diff / [o]verwrite", output)
            # 自動スキップは理由とタイムスタンプを添えて可視化する
            self.assertIn(f"Skipped: {dst} (前回確認時と同じ差分です:", output)
            self.assertEqual(len(list(session.state_dir.iterdir())), 1, output)

    def test_smart_copy_reprompt_flag_values_toggle_repeated_prompt(self):
        """SETTINGFILES_DIFF_REVIEW_REPROMPT の値で反復プロンプトが切り替わる。"""
        cases = (
            ("1", True),
            ("yes", True),
            ("0", False),
        )
        for value, expect_prompt in cases:
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as tmpdir:
                    session = ZshSession(Path(tmpdir))
                    src = Path(tmpdir) / "src.txt"
                    dst = Path(tmpdir) / "dst.txt"
                    src.write_text("new\n", encoding="utf-8")
                    dst.write_text("old\n", encoding="utf-8")
                    script = (
                        "source shell/zsh/alias/utils.zsh; "
                        f"smart_copy {quote(src)} {quote(dst)}"
                    )

                    seed = session.run(script, "s\n", reprompt=True)
                    self.assertEqual(seed.returncode, 0, combined_output(seed))

                    result = session.run(
                        script,
                        "s\n",
                        extra_env={"SETTINGFILES_DIFF_REVIEW_REPROMPT": value},
                    )
                    output = combined_output(result)

                    self.assertEqual(result.returncode, 0, output)
                    self.assertEqual(dst.read_text(encoding="utf-8"), "old\n")
                    if expect_prompt:
                        self.assertIn("前回確認時と同じ差分です:", output)
                        self.assertIn(
                            "[s]kip / [v]iew diff / [o]verwrite (default: s):", output
                        )
                    else:
                        self.assertNotIn("[s]kip / [v]iew diff / [o]verwrite", output)

    def test_smart_merge_json_merge_branch_auto_skips_with_keep_by_default(self):
        """merge 分岐の自動スキップは keep として扱われ、正常終了する。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text(json.dumps({"a": 2, "c": 3}), encoding="utf-8")
            dst.write_text(json.dumps({"a": 1, "b": 1}), encoding="utf-8")
            script = (
                "source shell/zsh/alias/utils.zsh; "
                f"smart_merge_json {quote(src)} {quote(dst)} src dst"
            )

            seed = session.run(script, "k\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script)
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertEqual(json.loads(dst.read_text(encoding="utf-8")), {"a": 1, "b": 1})
            self.assertNotIn("前回確認時と同じ差分です: 2", output)
            self.assertNotIn("=== Differences found ===", output)
            self.assertIn("前回確認時と同じ差分のため自動スキップしました:", output)
            self.assertIn("Skipped: dst", output)

    def test_smart_merge_json_fallback_branch_auto_skips_by_default(self):
        """不正 JSON の fallback 分岐も既定で自動スキップする。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text(json.dumps({"a": 1}), encoding="utf-8")
            dst.write_text("not json\n", encoding="utf-8")
            script = (
                "source shell/zsh/alias/utils.zsh; "
                f"smart_merge_json {quote(src)} {quote(dst)} src dst"
            )

            seed = session.run(script, "s\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script)
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertEqual(dst.read_text(encoding="utf-8"), "not json\n")
            self.assertNotIn("[s]kip / [v]iew diff / [o]verwrite", output)
            self.assertIn("Skipped: dst (前回確認時と同じ差分です:", output)

    def test_make_symlink_repeated_conflict_auto_skips_by_default(self):
        """make_symlink には SMART_MERGE_ACTION ゲートが無いため個別に pin する。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.write_text("source\n", encoding="utf-8")
            dst.write_text("existing\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}"

            seed = session.run(script, "n\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script)
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn("シンボリックリンクではない既存パスがあります:", output)
            self.assertNotIn("[s]kip / [v]iew change / [o]verwrite", output)
            self.assertIn(f"Skipped: {dst} (前回確認時と同じ差分です:", output)
            self.assertFalse(dst.is_symlink())
            self.assertEqual(dst.read_text(encoding="utf-8"), "existing\n")

    def test_diff_review_mktemp_json_returns_distinct_files_with_trailing_tmpdir_slash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            temp_dir = Path(tmpdir) / "tmp"
            temp_dir.mkdir()
            stale_literal = temp_dir / "settingfiles_diff_review_XXXXXX.json"
            script = (
                "source shell/zsh/alias/utils.zsh; "
                "first=$(_diff_review_mktemp_json); "
                "second=$(_diff_review_mktemp_json); "
                "print -r -- \"$first\"; "
                "print -r -- \"$second\"; "
                "[[ -e \"$first\" && -e \"$second\" ]]"
            )

            result = session.run(script, extra_env={"TMPDIR": f"{temp_dir}/"})
            output = combined_output(result)
            paths = [Path(line) for line in result.stdout.splitlines()]

            self.assertEqual(result.returncode, 0, output)
            self.assertEqual(len(paths), 2, output)
            self.assertNotEqual(paths[0], paths[1])
            self.assertTrue(paths[0].exists())
            self.assertTrue(paths[1].exists())
            self.assertNotEqual(paths[0], stale_literal)
            self.assertNotEqual(paths[1], stale_literal)
            self.assertNotIn("//", paths[0].as_posix())
            self.assertNotIn("//", paths[1].as_posix())

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
                reprompt=True,
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

            seed = session.run(script, "s\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "v\ns\n", reprompt=True)
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

            seed = session.run(script, "s\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            src.write_bytes(b"\x00new-two\n")
            result = session.run(script, "s\n", reprompt=True)
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

            seed = session.run(script, "k\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, extra_env={"SMART_MERGE_ACTION": "keep"}, reprompt=True)
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

            seed = session.run(script, "k\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "k\n", reprompt=True)
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

    @unittest.skipIf(shutil.which("jq", path=SYSTEM_PATH) is None, "jq is required")
    def test_smart_merge_json_works_with_stale_literal_mktemp_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            temp_dir = Path(tmpdir) / "tmp"
            temp_dir.mkdir()
            stale_literal = temp_dir / "settingfiles_diff_review_XXXXXX.json"
            stale_literal.write_text("stale\n", encoding="utf-8")
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text('{"a":2,"b":1}\n', encoding="utf-8")
            dst.write_text('{"a":1,"c":3}\n', encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; smart_merge_json {quote(src)} {quote(dst)} src dst"

            result = session.run(script, "k\n", extra_env={"TMPDIR": f"{temp_dir}/"})
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("Skipped: dst", output)
            self.assertEqual(stale_literal.read_text(encoding="utf-8"), "stale\n")

    @unittest.skipIf(shutil.which("jq", path=SYSTEM_PATH) is None, "jq is required")
    def test_smart_merge_json_merge_action_removes_tmpdir_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            temp_dir = Path(tmpdir) / "tmp"
            temp_dir.mkdir()
            src = Path(tmpdir) / "src.json"
            dst = Path(tmpdir) / "dst.json"
            src.write_text('{"a":2,"b":1}\n', encoding="utf-8")
            dst.write_text('{"a":1,"c":3}\n', encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; smart_merge_json {quote(src)} {quote(dst)} src dst"

            result = session.run(
                script,
                extra_env={"TMPDIR": f"{temp_dir}/", "SMART_MERGE_ACTION": "merge_src"},
            )
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("Applying merge result to destination: dst", output)
            self.assertEqual(json.loads(dst.read_text(encoding="utf-8")), {"a": 2, "b": 1, "c": 3})
            self.assertEqual(list(temp_dir.iterdir()), [])

    def test_make_symlink_repeated_conflict_shows_skip_first_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.write_text("source\n", encoding="utf-8")
            dst.write_text("existing\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}"

            seed = session.run(script, "n\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "s\n", reprompt=True)
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn("[s]kip / [v]iew change / [o]verwrite (default: s):", output)
            self.assertFalse(dst.is_symlink())
            self.assertEqual(dst.read_text(encoding="utf-8"), "existing\n")

    def test_make_symlink_initial_conflict_shows_detailed_differences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session = ZshSession(root)

            cases = (
                ("file", "source\n", "existing\n", "=== Differences found ==="),
                ("binary", b"\x00source\n", b"\x00existing\n", "=== Differences found ==="),
                ("type_mismatch", None, "existing\n", "Comparison unavailable:"),
            )
            for name, source_content, existing_content, expected_marker in cases:
                with self.subTest(name=name):
                    case_root = root / name
                    case_root.mkdir()
                    src = case_root / "src"
                    dst = case_root / "dst"
                    if name == "type_mismatch":
                        src.mkdir()
                    elif name == "binary":
                        src.write_bytes(source_content)
                    else:
                        src.write_text(source_content, encoding="utf-8")

                    if name == "binary":
                        dst.write_bytes(existing_content)
                    else:
                        dst.write_text(existing_content, encoding="utf-8")

                    result = session.run(
                        f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}",
                        "n\n",
                    )
                    output = combined_output(result)

                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn(f"Existing path: {dst}", output)
                    self.assertIn(f"Source path: {src}", output)
                    self.assertIn(expected_marker, output)
                    self.assertIn("シンボリックリンクではない既存パスがあります:", output)
                    self.assertFalse(dst.is_symlink())
                    if name == "binary":
                        self.assertEqual(dst.read_bytes(), existing_content)
                    else:
                        self.assertEqual(dst.read_text(encoding="utf-8"), existing_content)

            src_dir = root / "directory-src"
            destination_root = root / "directory-destination"
            dst_dir = destination_root / src_dir.name
            src_dir.mkdir()
            destination_root.mkdir()
            dst_dir.mkdir()
            (src_dir / "changed.txt").write_text("source\n", encoding="utf-8")
            (src_dir / "added.txt").write_text("added\n", encoding="utf-8")
            (dst_dir / "changed.txt").write_text("existing\n", encoding="utf-8")
            (dst_dir / "removed.txt").write_text("removed\n", encoding="utf-8")

            result = session.run(
                f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src_dir)} {quote(destination_root)}",
                "n\n",
            )
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("=== Directory differences found ===", output)
            self.assertIn("added.txt", output)
            self.assertIn("removed.txt", output)
            self.assertFalse(dst_dir.is_symlink())
            self.assertEqual(
                (dst_dir / "changed.txt").read_text(encoding="utf-8"),
                "existing\n",
            )
            self.assertEqual(
                (dst_dir / "removed.txt").read_text(encoding="utf-8"),
                "removed\n",
            )
            self.assertFalse((dst_dir / "added.txt").exists())

            reverse_src = root / "reverse-source"
            reverse_destination_root = root / "reverse-destination"
            reverse_existing_dir = reverse_destination_root / reverse_src.name
            reverse_src.write_text("source\n", encoding="utf-8")
            reverse_destination_root.mkdir()
            reverse_existing_dir.mkdir()
            (reverse_existing_dir / "retained.txt").write_text(
                "retained\n", encoding="utf-8"
            )

            result = session.run(
                "source shell/zsh/alias/utils.zsh; "
                f"make_symlink {quote(reverse_src)} {quote(reverse_destination_root)}",
                "n\n",
            )
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn(f"Existing path: {reverse_existing_dir}", output)
            self.assertIn("Existing type: directory", output)
            self.assertIn(f"Source path: {reverse_src}", output)
            self.assertIn("Source type: file", output)
            self.assertIn("Comparison unavailable: source is file; existing path is directory.", output)
            self.assertTrue(reverse_existing_dir.is_dir())
            self.assertFalse(reverse_existing_dir.is_symlink())
            self.assertEqual(
                (reverse_existing_dir / "retained.txt").read_text(encoding="utf-8"),
                "retained\n",
            )

    def test_make_symlink_source_change_invalidates_review_signature(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.write_text("source one\n", encoding="utf-8")
            dst.write_text("existing\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}"

            seed = session.run(script, "n\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            src.write_text("source two\n", encoding="utf-8")
            result = session.run(script, "n\n", reprompt=True)
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn("前回確認時と同じ差分です:", output)
            self.assertIn("=== Differences found ===", output)
            self.assertEqual(dst.read_text(encoding="utf-8"), "existing\n")

    def test_make_symlink_repeated_view_shows_detailed_change_and_confirm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session = ZshSession(Path(tmpdir))
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.write_text("source\n", encoding="utf-8")
            dst.write_text("existing\n", encoding="utf-8")
            script = f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}"

            seed = session.run(script, "n\n", reprompt=True)
            self.assertEqual(seed.returncode, 0, combined_output(seed))

            result = session.run(script, "v\nn\n", reprompt=True)
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("前回確認時と同じ差分です:", output)
            self.assertIn(f"Existing path: {dst}", output)
            self.assertIn("Existing type: file", output)
            self.assertIn(f"Source path: {src}", output)
            self.assertIn("Source type: file", output)
            self.assertIn(f"Intended symlink: {dst} -> {src}", output)
            self.assertIn("=== Differences found ===", output)
            self.assertIn("シンボリックリンクではない既存パスがあります:", output)
            self.assertFalse(dst.is_symlink())
            self.assertEqual(dst.read_text(encoding="utf-8"), "existing\n")

    def test_make_symlink_directory_falls_back_to_diff_when_difft_is_hidden(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session = ZshSession(root)
            src_dir = root / "source"
            destination_root = root / "destination"
            dst_dir = destination_root / src_dir.name
            safe_bin = root / "safe-bin"
            src_dir.mkdir()
            destination_root.mkdir()
            dst_dir.mkdir()
            safe_bin.mkdir()

            for command_name in (
                "basename",
                "awk",
                "date",
                "diff",
                "dirname",
                "find",
                "mkdir",
                "mktemp",
                "shasum",
                "sort",
                "stat",
                "zsh",
            ):
                executable = shutil.which(command_name, path=SYSTEM_PATH)
                self.assertIsNotNone(executable, command_name)
                (safe_bin / command_name).symlink_to(executable)

            (src_dir / "changed.txt").write_text("source\n", encoding="utf-8")
            (src_dir / "added.txt").write_text("added\n", encoding="utf-8")
            (dst_dir / "changed.txt").write_text("existing\n", encoding="utf-8")
            (dst_dir / "removed.txt").write_text("removed\n", encoding="utf-8")

            result = session.run(
                f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src_dir)} {quote(destination_root)}",
                "n\n",
                {"PATH": str(safe_bin)},
            )
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIsNone(shutil.which("difft", path=str(safe_bin)))
            self.assertIn(
                f"diff -ru {dst_dir / 'changed.txt'} {src_dir / 'changed.txt'}", output
            )
            self.assertIn(f"Only in {src_dir}: added.txt", output)
            self.assertIn(f"Only in {dst_dir}: removed.txt", output)
            self.assertFalse(dst_dir.is_symlink())
            self.assertEqual(
                (dst_dir / "changed.txt").read_text(encoding="utf-8"), "existing\n"
            )
            self.assertEqual(
                (dst_dir / "removed.txt").read_text(encoding="utf-8"), "removed\n"
            )

    def test_make_symlink_same_content_directory_conflict_does_not_claim_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session = ZshSession(root)
            src_dir = root / "source"
            destination_root = root / "destination"
            dst_dir = destination_root / src_dir.name
            src_dir.mkdir()
            destination_root.mkdir()
            dst_dir.mkdir()

            for directory in (src_dir, dst_dir):
                (directory / "nested").mkdir()
                (directory / "top-level.txt").write_text("identical\n", encoding="utf-8")
                (directory / "nested" / "child.txt").write_text(
                    "also identical\n", encoding="utf-8"
                )

            destination_before = {
                path.relative_to(dst_dir): path.read_bytes()
                for path in dst_dir.rglob("*")
                if path.is_file()
            }
            result = session.run(
                f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src_dir)} {quote(destination_root)}",
                "n\n",
            )
            output = combined_output(result)
            destination_after = {
                path.relative_to(dst_dir): path.read_bytes()
                for path in dst_dir.rglob("*")
                if path.is_file()
            }

            self.assertEqual(result.returncode, 0, output)
            self.assertIn("=== No content differences found ===", output)
            self.assertNotIn("=== Directory differences found ===", output)
            self.assertNotIn("diff -ru", output)
            self.assertNotIn("Only in ", output)
            self.assertIn("シンボリックリンクではない既存パスがあります:", output)
            self.assertFalse(dst_dir.is_symlink())
            self.assertEqual(destination_after, destination_before)

    def test_make_symlink_same_content_file_conflict_does_not_claim_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session = ZshSession(root)
            src = root / "src"
            dst = root / "dst"
            content = "identical\n"
            src.write_text(content, encoding="utf-8")
            dst.write_text(content, encoding="utf-8")

            result = session.run(
                f"source shell/zsh/alias/utils.zsh; make_symlink {quote(src)} {quote(dst)}",
                "n\n",
            )
            output = combined_output(result)

            self.assertEqual(result.returncode, 0, output)
            self.assertIn(f"Existing path: {dst}", output)
            self.assertIn(f"Source path: {src}", output)
            self.assertIn("=== No content differences found ===", output)
            self.assertNotIn("=== Differences found ===", output)
            self.assertIn("シンボリックリンクではない既存パスがあります:", output)
            self.assertFalse(dst.is_symlink())
            self.assertEqual(dst.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
