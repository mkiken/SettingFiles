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
ZSH = shutil.which("zsh")


class FwtTest(unittest.TestCase):
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
            "wml",
            "#!/bin/sh\nprintf 'worktree branch x x x path\\n'\n"
            "printf 'feature x x x x %s\\n' \"$FWT_WORKTREE\"\n",
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
            "else\n"
            "  printf 'feature\t%s\\n' \"$FWT_WORKTREE\"\n"
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

    def run_fwt(self, command="fwt", *args, tmux=False, extra_env=None):
        for path in (self.root / "filter-count", self.tmux_log):
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
            "TMUX": "",
            **({"TMUX": "test-client"} if tmux else {}),
            **(extra_env or {}),
        }
        command_line = " ".join([command, *args])
        script = f'''
            source "{TMUX_ALIASES}"
            source "{GIT_FILTER}"
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

    def test_moves_current_shell_without_tmux_or_rename(self):
        result, values = self.run_fwt()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.worktree))
        self.assertEqual(self.tmux_calls(), [])

    def test_creates_window_for_flag_and_alias(self):
        for command in ("fwt -w", "fwtw"):
            with self.subTest(command=command):
                result, values = self.run_fwt(command, tmux=True)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "0", result.stderr)
                self.assertEqual(
                    self.tmux_calls(), ["new-window", "-c", str(self.worktree)]
                )

    def test_creates_and_switches_session_for_flag_and_alias(self):
        for command in ("fwt -s", "fwts"):
            with self.subTest(command=command):
                result, values = self.run_fwt(
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
        cases = ("fwt -w -s", "fwt -x", "fwt path", "fwt -- path")
        for command in cases:
            with self.subTest(command=command):
                result, values = self.run_fwt(command)

                self.assertEqual(values["__STATUS"], "2")
                self.assertIn("Usage: fwt [-w|-s]", result.stderr)

    def test_requires_a_tmux_client_for_window_and_session_modes(self):
        for command in ("fwt -w", "fwt -s"):
            with self.subTest(command=command):
                result, values = self.run_fwt(command)

                self.assertEqual(values["__STATUS"], "1")
                self.assertIn("tmux内で実行してください", result.stderr)

    def test_returns_sigint_when_selection_cannot_complete(self):
        cases = (
            ("zoxide is unavailable", {"PATH": "/nonexistent"}),
            ("no repositories", {"FWT_ZOXIDE_LIST": ""}),
            ("selection cancelled", {"FWT_FILTER_CANCEL": "1"}),
        )
        for description, extra_env in cases:
            with self.subTest(description=description):
                result, values = self.run_fwt(extra_env=extra_env)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["__STATUS"], "130", result.stderr)


if __name__ == "__main__":
    unittest.main()
