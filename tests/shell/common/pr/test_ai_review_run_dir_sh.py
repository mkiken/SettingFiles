import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_review_run_dir.sh"


class AiReviewRunDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.work = base / "work"
        self.cache = base / "cache"
        self.bin = base / "bin"
        self.trash_log = base / "trash.log"
        self.work.mkdir()
        self.bin.mkdir()
        # trashスタブ: 呼び出しをログに追記し、実体をmvで退避する(rm系は使わない)
        trash_stub = self.bin / "trash"
        trash_stub.write_text(
            "#!/bin/bash\n"
            f'printf \'%s\\n\' "$@" >> "{self.trash_log}"\n'
            f'mkdir -p "{base}/trashed"\n'
            f'mv "$@" "{base}/trashed/"\n'
        )
        trash_stub.chmod(trash_stub.stat().st_mode | stat.S_IEXEC)
        subprocess.run(["git", "init", "-q"], cwd=self.work, check=True)

    def run_script(self, *args, remote="git@github.com:owner/repo.git", run_id="20260726-0000"):
        subprocess.run(
            ["git", "remote", "remove", "origin"],
            cwd=self.work, capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", remote],
            cwd=self.work, check=True,
        )
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            AI_REVIEW_CACHE_ROOT=str(self.cache),
            AI_REVIEW_RUN_ID=run_id,
        )
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=self.work, env=env, capture_output=True, text=True,
        )

    def test_create_outputs_run_dir_and_latest_link(self):
        result = self.run_script("123")
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = Path(result.stdout.strip())
        self.assertTrue(run_dir.is_dir())
        self.assertEqual(run_dir.name, "20260726-0000")
        self.assertEqual(run_dir.parent.name, "pr-123")
        self.assertEqual(run_dir.parent.parent.name, "owner__repo")
        latest = run_dir.parent / "latest"
        self.assertTrue(latest.is_symlink())
        self.assertEqual(os.readlink(latest), "20260726-0000")

    def test_repo_slug_parsing(self):
        cases = [
            ("git@github.com:owner/repo.git", "owner__repo"),
            ("https://github.com/owner/repo.git", "owner__repo"),
            ("https://github.com/owner/repo", "owner__repo"),
            ("ssh://git@github.com/owner/repo.git", "owner__repo"),
        ]
        for remote, expected in cases:
            with self.subTest(remote=remote):
                result = self.run_script("7", remote=remote)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"/{expected}/pr-7/", result.stdout)

    def test_latest_resolves_newest_run(self):
        self.run_script("123", run_id="20260726-0000")
        self.run_script("123", run_id="20260726-0100")
        result = self.run_script("--latest", "123")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith("pr-123/20260726-0100"))

    def test_latest_fails_when_no_runs(self):
        result = self.run_script("--latest", "999")
        self.assertNotEqual(result.returncode, 0)

    def test_retention_trashes_only_beyond_keep(self):
        # 境界値: keep=5 に対して 4, 5, 7 ラン
        cases = [(4, 0), (5, 0), (7, 2)]
        for total, expected_trashed in cases:
            with self.subTest(total=total):
                if self.trash_log.exists():
                    self.trash_log.unlink()
                for i in range(total):
                    self.run_script(str(1000 + total), run_id=f"20260726-{i:04d}")
                trashed = (
                    self.trash_log.read_text().strip().splitlines()
                    if self.trash_log.exists() else []
                )
                self.assertEqual(len(trashed), expected_trashed)
                if expected_trashed:
                    # 最古のランから順にtrashされる
                    self.assertTrue(trashed[0].endswith("20260726-0000"))

    def test_missing_pr_number_fails(self):
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
