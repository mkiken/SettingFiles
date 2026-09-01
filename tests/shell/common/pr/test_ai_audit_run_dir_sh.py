import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_audit_run_dir.sh"


class AiAuditRunDirTest(unittest.TestCase):
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

    def run_script(self, *args, run_id="20260901-120000", keep_runs=None, cwd=None):
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            AI_AUDIT_CACHE_ROOT=str(self.cache),
            AI_AUDIT_RUN_ID=run_id,
        )
        if keep_runs is not None:
            env["AI_AUDIT_KEEP_RUNS"] = str(keep_runs)
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=cwd or self.work, env=env, capture_output=True, text=True,
        )

    def test_create_returns_platform_scoped_path(self):
        result = self.run_script("claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = Path(result.stdout.strip())
        self.assertTrue(run_dir.is_dir())
        self.assertEqual(run_dir, self.cache / "claude" / "20260901-120000")

    def test_latest_symlink_points_at_the_new_run(self):
        created = Path(self.run_script("claude").stdout.strip())
        result = self.run_script("--latest", "claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), created.resolve())

    def test_platforms_do_not_share_a_directory(self):
        claude = Path(self.run_script("claude").stdout.strip())
        codex = Path(self.run_script("codex").stdout.strip())
        self.assertNotEqual(claude, codex)
        self.assertEqual(codex, self.cache / "codex" / "20260901-120000")

    def test_invalid_platform_is_rejected(self):
        result = self.run_script("bogus")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不正なプラットフォーム", result.stderr)

    def test_latest_fails_cleanly_when_no_run_exists(self):
        result = self.run_script("--latest", "gemini")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("最新ランが見つかりません", result.stderr)

    def test_works_outside_a_git_repository(self):
        # config-auditはリポジトリ外でも走るため、git originに依存してはならない
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        result = self.run_script("claude", cwd=outside)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(Path(result.stdout.strip()).is_dir())

    def test_old_runs_are_pruned_with_trash(self):
        for index in range(4):
            self.run_script("claude", run_id=f"2026090{index}-120000", keep_runs=2)
        remaining = sorted(
            path.name for path in (self.cache / "claude").iterdir()
            if path.is_dir() and not path.is_symlink()
        )
        self.assertEqual(remaining, ["20260902-120000", "20260903-120000"])
        trashed = self.trash_log.read_text(encoding="utf-8").split()
        self.assertEqual(len(trashed), 2)

    def test_pruning_keeps_five_runs_by_default(self):
        for index in range(7):
            self.run_script("claude", run_id=f"2026090{index}-120000")
        remaining = [
            path for path in (self.cache / "claude").iterdir()
            if path.is_dir() and not path.is_symlink()
        ]
        self.assertEqual(len(remaining), 5)


if __name__ == "__main__":
    unittest.main()
