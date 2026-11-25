"""shell/herdr/herdr_space_pr.zsh の単体テスト。

実herdr/ghには触れず、fake herdr（HERDR_BIN_PATH）とfake ghが呼び出しを記録する。
gh呼び出しはバックグラウンドなので、ログが揃うまでポーリングで待つ。
"""
import os
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

SCRIPT = REPO_ROOT / "shell/herdr/herdr_space_pr.zsh"

FAKE_HERDR = """#!/bin/sh
echo "$*" >> "$FAKE/herdr_calls"
exit 0
"""

FAKE_GH = """#!/bin/sh
echo "$*" >> "$FAKE/gh_calls"
[ -f "$FAKE/gh_fail" ] && exit 1
echo 123
"""

# HERDR_BIN_PATHがPATH上の別herdrより優先されること（実インスタンスを書き換えない）を
# 確かめるための罠。呼ばれたら痕跡を残す。
TRAP_HERDR = """#!/bin/sh
echo "trap invoked: $*" >> "$FAKE/trap_log"
exit 0
"""


def write_exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class HerdrSpacePrTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.fake = self.root / "fake"
        self.bin = self.root / "bin"
        self.decoy_bin = self.root / "decoy"
        for d in (self.fake, self.bin, self.decoy_bin):
            d.mkdir()
        write_exe(self.bin / "herdr", FAKE_HERDR)
        write_exe(self.bin / "gh", FAKE_GH)
        write_exe(self.decoy_bin / "herdr", TRAP_HERDR)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git_env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        for args in (["init", "-q", "-b", "feature/x"],
                     ["-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "--allow-empty", "-m", "init"]):
            subprocess.run(["git", *args], cwd=self.repo, check=True,
                           env=sanitized_env(git_env), capture_output=True)
        self.plain = self.root / "plain"
        self.plain.mkdir()

    def run_precmd(self, cwd: Path, calls: int = 1, **env_overrides):
        env = sanitized_env({
            "FAKE": str(self.fake),
            "HERDR_BIN_PATH": str(self.bin / "herdr"),
            "HERDR_WORKSPACE_ID": "w1",
            # decoyを先頭に置き、PATH解決のherdrが呼ばれたら罠に残る
            "PATH": f"{self.decoy_bin}:{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(self.root),
        })
        env.update(env_overrides)
        env = {k: v for k, v in env.items() if v is not None}
        script = (
            'add-zsh-hook() { :; }\n'
            'source "${1}"\n'
            f'for i in {{1..{calls}}}; do _herdr_space_pr_precmd; done\n'
        )
        subprocess.run(["zsh", "-fc", script, "zsh", str(SCRIPT)],
                       cwd=cwd, env=env, check=True, capture_output=True, timeout=30)

    def read(self, name: str) -> list[str]:
        p = self.fake / name
        return p.read_text().splitlines() if p.exists() else []

    def wait_for(self, name: str, count: int = 1) -> list[str]:
        for _ in range(100):
            lines = self.read(name)
            if len(lines) >= count:
                return lines
            time.sleep(0.05)
        return self.read(name)

    def test_pr_found_reports_number_token(self):
        self.run_precmd(self.repo)
        self.assertEqual(
            self.wait_for("herdr_calls"),
            ["workspace report-metadata w1 --source space-pr --token pr=#123"],
        )
        self.assertEqual(self.read("gh_calls"), ["pr view feature/x --json number -q .number"])
        # HERDR_BIN_PATH優先: PATH上のherdr（罠）は呼ばれない
        self.assertEqual(self.read("trap_log"), [])

    def test_no_pr_clears_token(self):
        (self.fake / "gh_fail").touch()
        self.run_precmd(self.repo)
        self.assertEqual(
            self.wait_for("herdr_calls"),
            ["workspace report-metadata w1 --source space-pr --clear-token pr"],
        )

    def test_outside_git_repo_clears_token_without_gh(self):
        self.run_precmd(self.plain)
        self.assertEqual(
            self.wait_for("herdr_calls"),
            ["workspace report-metadata w1 --source space-pr --clear-token pr"],
        )
        self.assertEqual(self.read("gh_calls"), [])

    def test_detached_head_clears_token_without_gh(self):
        subprocess.run(["git", "checkout", "-q", "--detach"], cwd=self.repo,
                       check=True, env=sanitized_env(), capture_output=True)
        self.run_precmd(self.repo)
        self.assertEqual(
            self.wait_for("herdr_calls"),
            ["workspace report-metadata w1 --source space-pr --clear-token pr"],
        )
        self.assertEqual(self.read("gh_calls"), [])

    def test_same_branch_within_ttl_queries_gh_once(self):
        self.run_precmd(self.repo, calls=2)
        self.wait_for("herdr_calls")
        # 2回目の照会が(誤って)走るならここまでに現れる
        time.sleep(0.3)
        self.assertEqual(len(self.read("gh_calls")), 1)
        self.assertEqual(len(self.read("herdr_calls")), 1)

    def test_skipped_inside_tmux(self):
        self.run_precmd(self.repo, TMUX="/tmp/tmux-1/default,1,0")
        time.sleep(0.3)
        self.assertEqual(self.read("gh_calls"), [])
        self.assertEqual(self.read("herdr_calls"), [])

    def test_skipped_without_workspace_id(self):
        self.run_precmd(self.repo, HERDR_WORKSPACE_ID=None)
        time.sleep(0.3)
        self.assertEqual(self.read("gh_calls"), [])
        self.assertEqual(self.read("herdr_calls"), [])


if __name__ == "__main__":
    unittest.main()
