import subprocess
import tempfile
import unittest

from support import REPO_ROOT, sanitized_env

GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
GITHUB_FILTER = REPO_ROOT / "shell/zsh/filter/github.zsh"

# br_local はfzfを起動するため fake へ差し替え、選択結果は $FAKE_BRANCH で制御する。
# gh も fake にして呼び出し引数を1行ずつログへ記録し、終了コードは $FAKE_GH_EXIT で制御する。
FAKE_PICKERS = '''
EXIT_CODE_SIGINT=130
br_local() {
    printf 'BR_LOCAL\\n' >&2
    printf '%s' "$FAKE_BRANCH"
}
save_history() {
    "$@"
}
gh() {
    printf '%s\\n' "$*" >> "$GH_LOG"
    return "${FAKE_GH_EXIT:-0}"
}
'''


def run_zsh(snippet, cwd, extra_env=None):
    env = sanitized_env(extra_env)
    env.setdefault("FAKE_BRANCH", "feat/x")
    return subprocess.run(
        ["zsh", "-c", f'source "{GIT_FILTER}"; source "{GITHUB_FILTER}"; {snippet}'],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


class FghsiTest(unittest.TestCase):
    """fghsi (gh stack init のブランチ選択ラッパー) を検証する。"""

    def test_selected_branch_runs_stack_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsi",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": "feat/x"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(gh_log) as f:
                self.assertEqual(f.read().strip(), "stack init --base feat/x")

    def test_cancel_skips_gh_invocation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            open(gh_log, "w").close()
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsi",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": ""},
            )
            self.assertEqual(result.returncode, 130)
            with open(gh_log) as f:
                self.assertEqual(f.read(), "")

    def test_extra_options_are_forwarded_after_base(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsi new-feature",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": "feat/x"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(gh_log) as f:
                self.assertEqual(f.read().strip(), "stack init --base feat/x new-feature")

    def test_gh_exit_code_is_propagated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsi",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": "feat/x", "FAKE_GH_EXIT": "17"},
            )
            self.assertEqual(result.returncode, 17)


class FghsaTest(unittest.TestCase):
    """fghsa (gh stack add のブランチ選択ラッパー) を検証する。"""

    def test_selected_branch_runs_stack_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsa",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": "feat/x"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(gh_log) as f:
                self.assertEqual(f.read().strip(), "stack add feat/x")

    def test_cancel_skips_gh_invocation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            open(gh_log, "w").close()
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsa",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": ""},
            )
            self.assertEqual(result.returncode, 130)
            with open(gh_log) as f:
                self.assertEqual(f.read(), "")

    def test_extra_options_are_forwarded_before_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            result = run_zsh(
                f'{FAKE_PICKERS}\nfghsa -m "msg"',
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": "feat/x"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(gh_log) as f:
                self.assertEqual(f.read().strip(), "stack add -m msg feat/x")

    def test_gh_exit_code_is_propagated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gh_log = f"{tmpdir}/gh.log"
            result = run_zsh(
                f"{FAKE_PICKERS}\nfghsa",
                cwd=tmpdir,
                extra_env={"GH_LOG": gh_log, "FAKE_BRANCH": "feat/x", "FAKE_GH_EXIT": "17"},
            )
            self.assertEqual(result.returncode, 17)


class StackPickerSourceInvariantTest(unittest.TestCase):
    """source直後にstdoutが汚れないこと（zshのループ内local再宣言によるstdout漏れの再発防止）を固定する。"""

    def test_sourcing_files_produces_no_stdout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["zsh", "-c", f'source "{GIT_FILTER}"; source "{GITHUB_FILTER}"'],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                env=sanitized_env(),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
