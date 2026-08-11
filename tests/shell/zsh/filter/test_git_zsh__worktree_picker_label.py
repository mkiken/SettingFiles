import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-c", f'source "{GIT_FILTER}"; {snippet}'],
        capture_output=True,
        text=True,
    )


class FilterGitWorktreePathLabelTest(unittest.TestCase):
    """_filter_git_worktree_path の--label-prefixオプトインと非回帰を検証する。

    filterをfakeへ差し替え、argvをそのまま出力するだけにして--prompt/--headerの
    実際の値を検証する。git worktree listもfakeにして候補を固定する。
    """

    FAKE_FILTER = 'filter() { printf "FILTER_ARGS %s\\n" "$*" >&2; }\n'
    FAKE_GIT_WORKTREE_LIST = '''
git() {
    if [[ "$1 $2" == "worktree list" ]]; then
        printf 'worktree /repo\\nbranch refs/heads/main\\n\\n'
        printf 'worktree /repo/wt\\nbranch refs/heads/feature\\n\\n'
        return 0
    fi
}
'''

    def test_target_picker_alone_keeps_default_prompt(self):
        # frws/repository-worktree等、既存呼び出し元の非回帰確認:
        # --label-prefix未指定時はprompt文言が従来のまま(worktree> )
        snippet = f'{self.FAKE_FILTER}{self.FAKE_GIT_WORKTREE_LIST}_filter_git_worktree_path --target-picker'
        result = run_zsh(snippet)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prompt worktree> ", result.stderr)

    def test_label_prefix_prepends_to_worktree_prompt(self):
        snippet = (
            f'{self.FAKE_FILTER}{self.FAKE_GIT_WORKTREE_LIST}'
            '_filter_git_worktree_path --target-picker --label-prefix review-subagents'
        )
        result = run_zsh(snippet)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prompt review-subagents worktree> ", result.stderr)

    def test_unknown_flag_still_rejected(self):
        # --target-picker / --label-prefix以外は従来どおりUsageエラーで拒否する
        result = run_zsh("_filter_git_worktree_path --bogus-flag")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Usage:", result.stderr)


class FilterZoxideGitRepoLabelTest(unittest.TestCase):
    """_filter_zoxide_git_repo の--label-prefixオプトインと非回帰を検証する。

    zoxideは実バイナリを使わずfakeへ差し替える。.gitディレクトリの有無判定
    ([[ -d "$d/.git" ]])は関数内でそのまま行われるため、実存する一時ディレクトリを
    候補として渡す（テスト用の一時ディレクトリのみを操作し、後始末する）。
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name).resolve() / "repo"
        (self.repo / ".git").mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run(self, extra_args=""):
        snippet = f'''
filter() {{ printf "FILTER_ARGS %s\\n" "$*" >&2; }}
zoxide() {{ printf '%s\\n' "{self.repo}"; }}
_filter_zoxide_git_repo {extra_args}
'''
        return run_zsh(snippet)

    def test_label_prefix_prepends_to_repo_prompt(self):
        result = self._run("--label-prefix review")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prompt review repo> ", result.stderr)

    def test_no_label_prefix_keeps_default_prompt(self):
        # 既存呼び出し元の非回帰確認: --label-prefix未指定時はprompt文言が従来のまま(repo> )
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prompt repo> ", result.stderr)


if __name__ == "__main__":
    unittest.main()
