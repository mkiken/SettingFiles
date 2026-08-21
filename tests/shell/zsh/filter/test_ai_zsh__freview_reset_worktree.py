import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

from .test_ai_zsh__freview_worktree import AI_FILTER, ZSH


class FreviewResetWorktreeTest(unittest.TestCase):
    """_freview_reset_worktreeの実gitでの検証。

    test_ai_zsh__freview_worktree.py / test_ai_zsh__freview_current_dir.py は
    restore/cleanをstubで吸収しているため「引数がこうだった」しか検証できず、
    --stagedの付け忘れや-xの有無といった実効性のバグを検出できない。
    ここだけは使い捨てリポジトリ（mktemp -d + git init）で実gitを走らせて検証する。
    本物のプロジェクトリポジトリでは絶対に実行しない
    （このリポジトリの破壊的コマンド検証方針）。
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        # macOSの/tmpは/private/tmpへのsymlinkのため、比較用に実パスへ解決しておく
        self.root = Path(self.temp_dir.name).resolve()

        # 安全ガード: 対象パスがテンポラリ配下でありこのリポジトリの外であることを
        # 実行前に確認する。誤って本物のリポジトリを渡す実装ミスを機械的に防ぐ
        tmp_root = Path(tempfile.gettempdir()).resolve()
        self.assertTrue(
            self.root.is_relative_to(tmp_root),
            f"{self.root} は一時ディレクトリ配下ではありません",
        )
        self.assertNotIn(REPO_ROOT.resolve(), self.root.parents)
        self.assertNotEqual(self.root, REPO_ROOT.resolve())

        self.repo = self.root / "wt"
        self.repo.mkdir()
        self.sibling = self.root / "sibling"
        self.sibling.mkdir()
        (self.sibling / "untouched.txt").write_text("sibling content\n")

        # 親のgit環境が漏れ込まないよう明示的に外す（未設定でも安全なようpopで除去）
        self._git_env = dict(os.environ)
        self._git_env.pop("GIT_DIR", None)
        self._git_env.pop("GIT_WORK_TREE", None)

        self._run_git(["init", "-q", "-b", "main"])
        self._run_git(["commit", "--allow-empty", "-q", "-m", "initial"])

    def _run_git(self, args, cwd=None):
        return subprocess.run(
            [
                "git",
                "-c",
                "user.email=test@example.com",
                "-c",
                "user.name=Test User",
                *args,
            ],
            cwd=cwd or self.repo,
            env=self._git_env,
            capture_output=True,
            text=True,
            check=True,
        )

    def _reset_worktree(self):
        script = f'''
            source "{AI_FILTER}"
            _freview_reset_worktree "{self.repo}"
            print -r -- "__STATUS=$?"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=self.root,
            capture_output=True,
            text=True,
            env={**os.environ, "EXIT_CODE_SIGINT": "130"},
        )
        status = None
        for line in result.stdout.splitlines():
            if line.startswith("__STATUS="):
                status = line.split("=", 1)[1]
        return result, status

    def _status_porcelain(self):
        return self._run_git(["status", "--porcelain"]).stdout

    def test_tracked_change_is_restored(self):
        tracked = self.repo / "tracked.txt"
        tracked.write_text("original\n")
        self._run_git(["add", "tracked.txt"])
        self._run_git(["commit", "-q", "-m", "add tracked"])
        tracked.write_text("modified\n")

        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(tracked.read_text(), "original\n")
        self.assertEqual(self._status_porcelain(), "")

    def test_staged_change_is_restored(self):
        # --stagedの付け忘れを検出する回帰ケース: stubでは検出できない
        tracked = self.repo / "tracked.txt"
        tracked.write_text("original\n")
        self._run_git(["add", "tracked.txt"])
        self._run_git(["commit", "-q", "-m", "add tracked"])
        tracked.write_text("modified\n")
        self._run_git(["add", "tracked.txt"])  # ステージ済みにする

        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(self._status_porcelain(), "")
        self.assertEqual(tracked.read_text(), "original\n")

    def test_untracked_file_and_directory_are_removed(self):
        (self.repo / "untracked.txt").write_text("junk\n")
        untracked_dir = self.repo / "untracked_dir"
        untracked_dir.mkdir()
        (untracked_dir / "nested.txt").write_text("junk\n")

        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertFalse((self.repo / "untracked.txt").exists())
        self.assertFalse(untracked_dir.exists())
        self.assertEqual(self._status_porcelain(), "")

    def test_gitignored_file_is_preserved(self):
        # -xを付けない設計の実証。stubでは検出できない最重要ケース
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        self._run_git(["add", ".gitignore"])
        self._run_git(["commit", "-q", "-m", "add gitignore"])
        ignored = self.repo / "ignored.txt"
        ignored.write_text("must survive\n")

        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertTrue(ignored.exists(), "gitignore対象ファイルは削除されてはならない")
        self.assertEqual(ignored.read_text(), "must survive\n")

    def test_mixed_state_is_fully_cleaned_in_one_call(self):
        tracked = self.repo / "tracked.txt"
        tracked.write_text("original\n")
        self._run_git(["add", "tracked.txt"])
        self._run_git(["commit", "-q", "-m", "add tracked"])
        tracked.write_text("modified\n")
        (self.repo / "untracked.txt").write_text("junk\n")

        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(self._status_porcelain(), "")
        self.assertEqual(tracked.read_text(), "original\n")
        self.assertFalse((self.repo / "untracked.txt").exists())

    def test_already_clean_is_idempotent(self):
        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(self._status_porcelain(), "")

    def test_runs_from_subdirectory_cleans_whole_repo(self):
        # パススペック:/の実証。サブディレクトリをcwdにしてもリポジトリ全体が対象になる
        subdir = self.repo / "sub"
        subdir.mkdir()
        (self.repo / "root_untracked.txt").write_text("junk\n")
        (subdir / "sub_untracked.txt").write_text("junk\n")

        script = f'''
            source "{AI_FILTER}"
            _freview_reset_worktree "{self.repo}"
            print -r -- "__STATUS=$?"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=subdir,
            capture_output=True,
            text=True,
            env={**os.environ, "EXIT_CODE_SIGINT": "130"},
        )
        status = next(
            line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__STATUS=")
        )

        self.assertEqual(status, "0", result.stderr)
        self.assertFalse((self.repo / "root_untracked.txt").exists())
        self.assertFalse((subdir / "sub_untracked.txt").exists())

    def test_does_not_affect_sibling_directory(self):
        (self.repo / "untracked.txt").write_text("junk\n")

        result, status = self._reset_worktree()

        self.assertEqual(status, "0", result.stderr)
        self.assertTrue((self.sibling / "untouched.txt").exists())
        self.assertEqual((self.sibling / "untouched.txt").read_text(), "sibling content\n")


if __name__ == "__main__":
    unittest.main()
