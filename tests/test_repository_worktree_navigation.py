import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
TMUX_ALIASES = REPO_ROOT / "shell/zsh/alias/tmux.zsh"
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"
AI_FILTER = REPO_ROOT / "shell/zsh/filter/ai.zsh"
ZSH = shutil.which("zsh")


class RepositoryWorktreeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.repo = self.root / "repo with space"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.worktree = self.root / "feature worktree"
        self.worktree.mkdir()
        self.tmux_log = self.root / "tmux.log"
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
            "zoxide",
            "#!/bin/sh\nprintf '%s\\n' \"$FWT_ZOXIDE_LIST\"\n",
        )
        self._write_executable(
            "git",
            "#!/bin/sh\n"
            "if [ \"$1\" = rev-parse ] && [ \"$2\" = --show-toplevel ]; then\n"
            "  printf '%s\\n' \"$FWT_REPO\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = worktree ] && [ \"$2\" = list ]; then\n"
            "  [ \"${FWT_NO_WORKTREE_OUTPUT:-}\" = 1 ] && exit 0\n"
            "  printf 'worktree %s\\n' \"$FWT_REPO\"\n"
            "  printf 'HEAD %s\\n' \"${FWT_REPO_SHA:-1111111repo}\"\n"
            "  printf 'branch refs/heads/%s\\n' \"${FWT_REPO_BRANCH:-main}\"\n"
            "  [ \"${FWT_ONLY_MAIN_WORKTREE:-}\" = 1 ] && exit 0\n"
            "  printf '\\n'\n"
            "  printf 'worktree %s\\n' \"$FWT_WORKTREE\"\n"
            "  printf 'HEAD %s\\n' \"${FWT_WORKTREE_SHA:-2222222worktree}\"\n"
            "  if [ \"${FWT_WORKTREE_DETACHED:-}\" = 1 ]; then\n"
            "    printf 'detached\\n'\n"
            "  else\n"
            "    printf 'branch refs/heads/%s\\n' \"${FWT_WORKTREE_BRANCH:-feature}\"\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "exec /usr/bin/git \"$@\"\n",
        )
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "count_file=\"$FWT_FILTER_COUNT\"\n"
            "count=0\n"
            "[ -f \"$count_file\" ] && count=$(cat \"$count_file\")\n"
            "printf '%s' $((count + 1)) > \"$count_file\"\n"
            "[ \"${FWT_FILTER_CANCEL:-}\" = 1 ] && exit 0\n"
            "if [ \"$count\" -eq 0 ]; then\n"
            "  printf '%s\\n' \"$FWT_REPO\"\n"
            "elif [ -n \"${FWT_FILTER_EXPECT_KEY:-}\" ]; then\n"
            "  printf '%s\\n' \"$FWT_FILTER_EXPECT_KEY\"\n"
            "  if [ \"${FWT_ONLY_MAIN_WORKTREE:-}\" = 1 ]; then\n"
            "    printf 'repo\\t%s\\n' \"$FWT_REPO\"\n"
            "  else\n"
            "    printf 'worktree\\t%s\\n' \"$FWT_WORKTREE\"\n"
            "  fi\n"
            "elif [ \"${FWT_FILTER_TARGET:-worktree}\" = repo ]; then\n"
            "  printf 'repo\\t%s\\n' \"$FWT_REPO\"\n"
            "else\n"
            "  printf 'worktree\\t%s\\n' \"$FWT_WORKTREE\"\n"
            "fi\n",
        )
        self._write_executable(
            "tmux",
            "#!/bin/sh\nprintf '%s\\n' \"$@\" >> \"$FWT_TMUX_LOG\"\n"
            "if [ \"$1\" = new-session ]; then\n"
            "  printf '%s\\n' \"${FWT_SESSION_NAME:-tmux-session}\"\n"
            "fi\n"
            "exit 0\n",
        )
        self._write_executable(
            "herdr",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" | tr '\\n' ' ' >> \"$FWT_HERDR_LOG\"\n"
            "printf '\\n' >> \"$FWT_HERDR_LOG\"\n"
            "if [ \"$1\" = workspace ] && [ \"$2\" = create ]; then\n"
            "  printf '{\"result\":{\"workspace\":{\"workspace_id\":\"ws-1\"},\"root_pane\":{\"pane_id\":\"p-1\"}}}\\n'\n"
            "elif [ \"$1\" = tab ] && [ \"$2\" = create ]; then\n"
            "  printf '{\"result\":{\"root_pane\":{\"pane_id\":\"p-1\"}}}\\n'\n"
            "fi\n"
            "exit 0\n",
        )

    def run_repository_worktree(
        self, command="repository-worktree", *args, tmux=False, herdr=False, extra_env=None
    ):
        for path in (self.root / "filter-count", self.tmux_log, self.herdr_log):
            if path.exists():
                path.unlink()
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWT_ZOXIDE_LIST": str(self.repo),
            "FWT_REPO": str(self.repo),
            "FWT_WORKTREE": str(self.worktree),
            "FWT_FILTER_COUNT": str(self.root / "filter-count"),
            "FWT_TMUX_LOG": str(self.tmux_log),
            "FWT_HERDR_LOG": str(self.herdr_log),
            "TMUX": "",
            "HERDR_ENV": "",
            **({"TMUX": "test-client"} if tmux else {}),
            **({"HERDR_ENV": "1"} if herdr else {}),
            **(extra_env or {}),
        }
        command_line = " ".join([command, *args])
        script = f'''
            source "{TMUX_ALIASES}"
            source "{AI_ALIASES}"
            source "{AI_FILTER}"
            source "{GIT_FILTER}"
            _chpwd_noise() {{ print -r -- "NOISE $PWD"; }}
            cdq() {{
                _CDQ_QUIET=1
                builtin cd "$@" 2>/dev/null
                unset _CDQ_QUIET
            }}
            chpwd() {{ [[ -z "$_CDQ_QUIET" ]] && _chpwd_noise; }}
            save_history() {{ "$@"; }}
            eval {command_line!r}
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
            print -r -- "__PWD=$PWD"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=self.root,
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

    def tmux_calls(self):
        return self.tmux_log.read_text().splitlines() if self.tmux_log.exists() else []

    def herdr_calls(self):
        return self.herdr_log.read_text().splitlines() if self.herdr_log.exists() else []

    def test_moves_current_shell_without_tmux_or_rename(self):
        result, values = self.run_repository_worktree()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.worktree))
        self.assertEqual(self.tmux_calls(), [])

    def test_creates_window_for_flag_and_alias(self):
        for command in ("repository-worktree -w", "frww"):
            with self.subTest(command=command):
                result, values = self.run_repository_worktree(command, tmux=True)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "0", result.stderr)
                self.assertEqual(
                    self.tmux_calls(), ["new-window", "-c", str(self.worktree)]
                )

    def test_creates_and_switches_session_for_flag_and_alias(self):
        for command in ("repository-worktree -s", "frws"):
            with self.subTest(command=command):
                result, values = self.run_repository_worktree(
                    command,
                    tmux=True,
                    extra_env={"FWT_SESSION_NAME": "generated-session"},
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "0", result.stderr)
                self.assertEqual(
                    self.tmux_calls(),
                    [
                        "new-session",
                        "-d",
                        "-P",
                        "-F",
                        "#S",
                        "-c",
                        str(self.worktree),
                        "switch-client",
                        "-t",
                        "generated-session",
                    ],
                )

    def test_rejects_invalid_arguments(self):
        cases = (
            "repository-worktree -w -s",
            "repository-worktree -x",
            "repository-worktree path",
            "repository-worktree -- path",
        )
        for command in cases:
            with self.subTest(command=command):
                result, values = self.run_repository_worktree(command)

                self.assertEqual(values["__STATUS"], "2")
                self.assertIn("Usage: repository-worktree [-w|-s]", result.stderr)

    def test_requires_a_multiplexer_for_window_and_session_modes(self):
        for command in ("repository-worktree -w", "repository-worktree -s"):
            with self.subTest(command=command):
                result, values = self.run_repository_worktree(command)

                self.assertEqual(values["__STATUS"], "1")
                self.assertIn("tmuxまたはHerdr内で実行してください", result.stderr)

    def test_creates_herdr_tab_for_window_mode(self):
        for command in ("repository-worktree -w", "frww"):
            with self.subTest(command=command):
                result, values = self.run_repository_worktree(command, herdr=True)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "0", result.stderr)
                self.assertEqual(self.tmux_calls(), [])
                calls = self.herdr_calls()
                self.assertEqual(len(calls), 1, calls)
                self.assertIn("tab create", calls[0])
                self.assertIn(f"--cwd {self.worktree}", calls[0])
                self.assertIn("--focus", calls[0])
                self.assertNotIn("--no-focus", calls[0])

    def test_creates_herdr_workspace_for_session_mode(self):
        for command in ("repository-worktree -s", "frws"):
            with self.subTest(command=command):
                result, values = self.run_repository_worktree(command, herdr=True)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "0", result.stderr)
                self.assertEqual(self.tmux_calls(), [])
                calls = self.herdr_calls()
                self.assertEqual(len(calls), 1, calls)
                self.assertIn("workspace create", calls[0])
                self.assertIn(f"--cwd {self.worktree}", calls[0])
                self.assertIn("--focus", calls[0])
                self.assertNotIn("--no-focus", calls[0])

    def test_popup_picker_routes_selected_worktree_by_accept_key(self):
        cases = (
            ("", "workspace create", ""),
            ("alt-t", "tab create", ""),
            ("ctrl-s", "pane split --pane w1:p1 --direction down", "w1:p1"),
            ("ctrl-v", "pane split --pane w1:p1 --direction right", "w1:p1"),
        )
        for key, command, active_pane_id in cases:
            with self.subTest(key=key or "enter"):
                extra_env = {"FWT_FILTER_EXPECT_KEY": key}
                if active_pane_id:
                    extra_env["HERDR_ACTIVE_PANE_ID"] = active_pane_id
                result, values = self.run_repository_worktree(
                    "_herdr_pick_worktree_target", herdr=True, extra_env=extra_env
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "0", result.stderr)
                calls = self.herdr_calls()
                self.assertEqual(len(calls), 1, calls)
                self.assertIn(command, calls[0])
                self.assertIn(f"--cwd {self.worktree}", calls[0])
                self.assertIn("--focus", calls[0])

    def test_popup_picker_shows_single_worktree_for_target_selection(self):
        result, values = self.run_repository_worktree(
            "_herdr_pick_worktree_target",
            herdr=True,
            extra_env={"FWT_ONLY_MAIN_WORKTREE": "1", "FWT_FILTER_EXPECT_KEY": "alt-t"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual((self.root / "filter-count").read_text(), "2")
        calls = self.herdr_calls()
        self.assertEqual(len(calls), 1, calls)
        self.assertIn("tab create", calls[0])
        self.assertIn(f"--cwd {self.repo}", calls[0])

    def test_popup_picker_split_requires_the_popup_source_pane(self):
        result, values = self.run_repository_worktree(
            "_herdr_pick_worktree_target",
            herdr=True,
            extra_env={"FWT_FILTER_EXPECT_KEY": "ctrl-s"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("発火元pane", result.stderr)
        self.assertEqual(self.herdr_calls(), [])

    def test_returns_sigint_when_selection_cannot_complete(self):
        cases = (
            ("zoxide is unavailable", {"PATH": "/nonexistent"}),
            ("no repositories", {"FWT_ZOXIDE_LIST": ""}),
            ("selection cancelled", {"FWT_FILTER_CANCEL": "1"}),
            ("no worktrees at all", {"FWT_NO_WORKTREE_OUTPUT": "1"}),
        )
        for description, extra_env in cases:
            with self.subTest(description=description):
                result, values = self.run_repository_worktree(extra_env=extra_env)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "130", result.stderr)

    def test_can_move_to_the_main_repository_itself(self):
        result, values = self.run_repository_worktree(extra_env={"FWT_FILTER_TARGET": "repo"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.repo))

    def test_skips_selection_and_moves_to_main_repo_when_no_additional_worktree(self):
        # 追加worktreeが無く本体のみの場合はfilterでの選択UIを出さず、直接本体に移動する
        result, values = self.run_repository_worktree(
            extra_env={"FWT_ONLY_MAIN_WORKTREE": "1"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.repo))

        filter_count_path = self.root / "filter-count"
        filter_call_count = (
            int(filter_count_path.read_text()) if filter_count_path.exists() else 0
        )
        # リポジトリ選択の1回のみでworktree選択は呼ばれない
        self.assertEqual(filter_call_count, 1)

    def test_moves_to_detached_worktree_shown_with_short_sha(self):
        # detached HEADのworktreeでも、ブランチ欄が短縮SHAになるだけで選択・移動自体は成功する
        result, values = self.run_repository_worktree(
            extra_env={"FWT_WORKTREE_DETACHED": "1", "FWT_WORKTREE_SHA": "abcdef0123456"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.worktree))


if __name__ == "__main__":
    unittest.main()
