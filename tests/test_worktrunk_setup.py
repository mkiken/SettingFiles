import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class WorktrunkSetupTest(unittest.TestCase):
    def test_brewfile_installs_worktrunk_without_workmux_tap(self):
        brewfile = (REPO_ROOT / "mac/Brewfile").read_text(encoding="utf-8")

        self.assertIn('brew "worktrunk"', brewfile)
        self.assertNotIn("workmux", brewfile)

    def test_git_setup_does_not_link_workmux_config(self):
        setup = (REPO_ROOT / "mac/initialization/git_setup.sh").read_text(encoding="utf-8")

        self.assertNotIn("workmux", setup)

    def test_worktrunk_shell_integration_follows_path_setup_before_filters(self):
        managed = (REPO_ROOT / "shell/zsh/managed.zsh").read_text(encoding="utf-8")
        shell_init = 'eval "$wt_shell_init"'

        self.assertIn("command -v wt >/dev/null 2>&1", managed)
        self.assertIn('wt_shell_init="$(command wt config shell init zsh)"', managed)
        self.assertIn(
            'wt_shell_init=${wt_shell_init//rm\\ -f\\ \\"\\$cd_file\\"\\ \\"\\$exec_file\\"/command\\ rm\\ -f\\ \\"\\$cd_file\\"\\ \\"\\$exec_file\\"}',
            managed,
        )
        self.assertIn(shell_init, managed)
        self.assertNotIn('eval "$(command wt config shell init zsh)"', managed)
        self.assertLess(managed.index("typeset -U path"), managed.index(shell_init))
        self.assertLess(managed.index(shell_init), managed.index("shell/zsh/filter/main.zsh"))

    def test_worktrunk_shell_integration_bypasses_rm_alias_for_cleanup(self):
        managed = (REPO_ROOT / "shell/zsh/managed.zsh").read_text(encoding="utf-8")
        start = managed.index("if command -v wt >/dev/null 2>&1; then")
        end = managed.index("\nfi", start) + len("\nfi")
        integration = managed[start:end]

        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            wt = bin_dir / "wt"
            wt.write_text(
                "#!/bin/zsh\n"
                "if [[ \"$*\" == \"config shell init zsh\" ]]; then\n"
                "  print -r -- 'wt() { local cd_file exec_file; cd_file=$(mktemp); exec_file=$(mktemp); rm -f \"$cd_file\" \"$exec_file\"; }'\n"
                "fi\n",
                encoding="utf-8",
            )
            wt.chmod(0o755)
            env = os.environ | {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
            result = subprocess.run(
                ["zsh", "-fc", f"alias rm='print ALIAS_RM'; {integration}; wt"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("ALIAS_RM", result.stdout)

    def test_worktrunk_functions_keep_remove_flags_user_controlled(self):
        aliases = (REPO_ROOT / "shell/zsh/alias/git.zsh").read_text(encoding="utf-8")

        self.assertIn("wtc() {", aliases)
        self.assertIn('wt switch --create "$@"', aliases)
        self.assertIn("wtl() {", aliases)
        self.assertIn('wt list "$@"', aliases)
        self.assertIn("wts() {", aliases)
        self.assertIn('wt switch "$@"', aliases)
        self.assertIn("wtr() {", aliases)
        self.assertIn('wt remove "$@"', aliases)
        self.assertNotIn("wt remove --", aliases)
        self.assertNotIn("wt create", aliases)
        self.assertNotIn("workmux", aliases)
        self.assertNotIn("_workmux_ensure_setup", aliases)

    def test_worktrunk_functions_forward_arguments(self):
        result = subprocess.run(
            [
                "zsh",
                "-fc",
                'source shell/zsh/alias/git.zsh; wt() { print -r -- "$@"; }; wtc topic --base main; wtl --all; wts topic; wtr; wtr --force topic',
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "switch --create topic --base main",
                "list --all",
                "switch topic",
                "switch",
                "remove --force topic",
            ],
        )


if __name__ == "__main__":
    unittest.main()
