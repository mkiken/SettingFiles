import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"
ZSH = shutil.which("zsh")


class FgwtFixture:
    """fgwtとfwmonで共有する隔離済みworktree fixture。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.worktree = self.root / "feature worktree"
        self.worktree.mkdir()
        self._write_fake_commands()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_executable(self, name: str, body: str):
        path = self.bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def _write_fake_commands(self):
        self._write_executable(
            "git",
            "#!/bin/sh\n"
            "if [ \"$1\" = worktree ] && [ \"$2\" = list ]; then\n"
            "  [ \"${FGWT_NO_WORKTREE_OUTPUT:-}\" = 1 ] && exit 0\n"
            "  printf 'worktree %s\\n' \"$FGWT_REPO\"\n"
            "  printf 'worktree %s\\n' \"$FGWT_WORKTREE\"\n"
            "  exit 0\n"
            "fi\n"
            "exec /usr/bin/git \"$@\"\n",
        )
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "[ \"${FGWT_FILTER_CANCEL:-}\" = 1 ] && exit 0\n"
            "if [ \"${FGWT_FILTER_TARGET:-worktree}\" = repo ]; then\n"
            "  printf '%s\\n' \"$FGWT_REPO\"\n"
            "else\n"
            "  printf '%s\\n' \"$FGWT_WORKTREE\"\n"
            "fi\n",
        )

    def run_fgwt(self, command="fgwt", extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FGWT_REPO": str(self.repo),
            "FGWT_WORKTREE": str(self.worktree),
            **(extra_env or {}),
        }
        script = f'''
            source "{GIT_FILTER}"
            save_history() {{ "$@"; }}
            eval {command!r}
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
            print -r -- "__PWD=$PWD"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=env,
        )
        values = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__")
        }
        return result, values


class FgwtTest(FgwtFixture, unittest.TestCase):
    """fgwt: 現在リポジトリのworktreeを選択してカレントpaneでcdする（zoxide非依存）"""

    def test_moves_current_shell_to_selected_worktree(self):
        result, values = self.run_fgwt()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.worktree))

    def test_can_move_to_the_main_repository_itself(self):
        result, values = self.run_fgwt(extra_env={"FGWT_FILTER_TARGET": "repo"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.repo))

    def test_returns_sigint_when_selection_cannot_complete(self):
        cases = (
            ("selection cancelled", {"FGWT_FILTER_CANCEL": "1"}),
            ("no worktrees at all", {"FGWT_NO_WORKTREE_OUTPUT": "1"}),
        )
        for description, extra_env in cases:
            with self.subTest(description=description):
                result, values = self.run_fgwt(extra_env=extra_env)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "130", result.stderr)


class FwmonTest(FgwtFixture, unittest.TestCase):
    """fwmon: 現在リポジトリのworktreeを選択して新しいtmux windowで開く"""

    def setUp(self):
        super().setUp()
        self.tmux_log = self.root / "tmux.log"
        self._write_executable(
            "tmux",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" >> \"$FWMON_TMUX_LOG\"\n",
        )

    def run_fwmon(self, extra_env=None):
        env = {
            "FWMON_TMUX_LOG": str(self.tmux_log),
            **(extra_env or {}),
        }
        return self.run_fgwt(command="fwmon", extra_env=env)

    def tmux_calls(self):
        return self.tmux_log.read_text().splitlines() if self.tmux_log.exists() else []

    def test_opens_selected_worktree_in_a_new_tmux_window(self):
        result, values = self.run_fwmon()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(
            self.tmux_calls(),
            ["new-window", "-c", str(self.worktree)],
        )

    def test_returns_sigint_when_selection_cannot_complete(self):
        result, values = self.run_fwmon(extra_env={"FGWT_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual(self.tmux_calls(), [])


class FgwtcTest(unittest.TestCase):
    """fgwtc: herdr専用。worktreeを選択してherdrの新タブで開く（cdのみ、AI起動なし）"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.worktree = self.root / "feature worktree"
        self.worktree.mkdir()
        self.herdr_log = self.root / "herdr.log"
        self._write_fake_commands()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_executable(self, name: str, body: str):
        path = self.bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def _write_fake_commands(self):
        self._write_executable(
            "git",
            "#!/bin/sh\n"
            "if [ \"$1\" = worktree ] && [ \"$2\" = list ]; then\n"
            "  [ \"${FGWT_NO_WORKTREE_OUTPUT:-}\" = 1 ] && exit 0\n"
            "  printf 'worktree %s\\n' \"$FGWT_REPO\"\n"
            "  printf 'worktree %s\\n' \"$FGWT_WORKTREE\"\n"
            "  exit 0\n"
            "fi\n"
            "exec /usr/bin/git \"$@\"\n",
        )
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "[ \"${FGWT_FILTER_CANCEL:-}\" = 1 ] && exit 0\n"
            "if [ \"${FGWT_FILTER_TARGET:-worktree}\" = repo ]; then\n"
            "  printf '%s\\n' \"$FGWT_REPO\"\n"
            "else\n"
            "  printf '%s\\n' \"$FGWT_WORKTREE\"\n"
            "fi\n",
        )
        self._write_executable(
            "herdr",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" >> \"$FGWTC_HERDR_LOG\"\n"
            "if [ \"$1\" = tab ] && [ \"$2\" = create ]; then\n"
            "  if [ \"${FGWTC_HERDR_CREATE_FAIL:-}\" = 1 ]; then\n"
            "    exit 1\n"
            "  fi\n"
            "  printf '%s' '{\"result\":{\"root_pane\":{\"pane_id\":\"pane-1\"}}}'\n"
            "  exit 0\n"
            "fi\n"
            "exit 0\n",
        )
        # 実jqがあればそれを使う。無い環境向けの最小フォールバックは用意しない
        # （テスト実行環境にjqがある前提。CI/開発機とも通常同梱）。

    def run_fgwtc(self, command="fgwtc", extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FGWT_REPO": str(self.repo),
            "FGWT_WORKTREE": str(self.worktree),
            "FGWTC_HERDR_LOG": str(self.herdr_log),
            "HERDR_ENV": "",
            "TMUX": "",
            **(extra_env or {}),
        }
        script = f'''
            source "{AI_ALIASES}"
            source "{GIT_FILTER}"
            eval {command!r}
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=env,
        )
        values = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__")
        }
        return result, values

    def herdr_calls(self):
        return self.herdr_log.read_text().splitlines() if self.herdr_log.exists() else []

    def test_opens_new_herdr_tab_for_selected_worktree(self):
        result, values = self.run_fgwtc(extra_env={"HERDR_ENV": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.herdr_calls()
        # tab create 直後、_herdr_wait_shell_ready がシェルready確認のマーカーecho +
        # pane wait-output を挟んでから本命(no-opの ':')を投入する。マーカー文字列自体は
        # $$/RANDOM由来で実行毎に変わるため、末尾の本命投入のみ厳密に検証する。
        self.assertEqual(
            calls[:7],
            [
                "tab",
                "create",
                "--cwd",
                str(self.worktree),
                "--label",
                "feature worktree",
                "--no-focus",
            ],
        )
        self.assertEqual(calls[-4:], ["pane", "run", "pane-1", ":"])
        self.assertTrue(any("__herdr_ready_" in line for line in calls))

    def test_rejects_when_not_in_herdr_environment(self):
        result, values = self.run_fgwtc(extra_env={"HERDR_ENV": ""})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("herdr環境専用", result.stderr)
        self.assertEqual(self.herdr_calls(), [])

    def test_rejects_in_tmux_environment_without_herdr(self):
        result, values = self.run_fgwtc(
            extra_env={"HERDR_ENV": "", "TMUX": "test-client"}
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertEqual(self.herdr_calls(), [])

    def test_returns_sigint_when_selection_cancelled(self):
        result, values = self.run_fgwtc(
            extra_env={"HERDR_ENV": "1", "FGWT_FILTER_CANCEL": "1"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual(self.herdr_calls(), [])

    def test_returns_sigint_when_no_worktrees(self):
        result, values = self.run_fgwtc(
            extra_env={"HERDR_ENV": "1", "FGWT_NO_WORKTREE_OUTPUT": "1"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual(self.herdr_calls(), [])

    def test_fails_when_tab_create_fails(self):
        result, values = self.run_fgwtc(
            extra_env={"HERDR_ENV": "1", "FGWTC_HERDR_CREATE_FAIL": "1"}
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        calls = self.herdr_calls()
        self.assertEqual(calls[0], "tab")
        self.assertEqual(calls[1], "create")
        self.assertNotIn("pane", calls)


if __name__ == "__main__":
    unittest.main()
