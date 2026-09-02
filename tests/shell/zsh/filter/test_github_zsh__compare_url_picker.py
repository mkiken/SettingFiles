import os
import subprocess
import tempfile
import unittest

from support import REPO_ROOT

GH_ALIASES = REPO_ROOT / "shell/zsh/alias/gh.zsh"
# _select_commit_hash_in_range が _extract_commit_hash (git.zsh) を再利用するため一緒にsourceする
GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
GITHUB_FILTER = REPO_ROOT / "shell/zsh/filter/github.zsh"

# openは実際のブラウザを起動してしまうため必ずfakeへ差し替える。
# br_org / _select_commit_hash はfzfを起動するため同様にfakeへ差し替え、
# 各段への引数と呼び出し有無だけをstderrで観測する。
FAKE_PICKERS = '''
EXIT_CODE_SIGINT=130
open() {
    printf 'OPEN %s\\n' "$*" >&2
}
save_history() {
    "$@"
}
br_org() {
    printf 'BR_ORG\\n' >&2
    printf '%s' "$FAKE_BRANCH"
}
_select_commit_hash() {
    printf 'SELECT_COMMIT header=%s limit=%s rev=%s\\n' "$1" "$2" "$3" >&2
    printf '%s' "$FAKE_BASE_HASH"
}
_select_commit_hash_in_range() {
    printf 'SELECT_RANGE header=%s range=%s limit=%s\\n' "$1" "$2" "$3" >&2
    printf '%s' "$FAKE_COMPARE_HASH"
}
'''


def _init_repo(path, remote_url):
    """使い捨てのgitリポジトリを作る。破壊的コマンドは実行しないが本物のリポジトリを触らないため隔離する。"""
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    subprocess.run(["git", "init", "-q"], cwd=path, env=env, check=True)
    if remote_url is not None:
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url], cwd=path, env=env, check=True
        )


def run_zsh(snippet, cwd=None, remote_url="git@github.com:owner/repo.git", extra_env=None):
    env = dict(os.environ)
    env.setdefault("FAKE_BRANCH", "main")
    env.setdefault("FAKE_BASE_HASH", "aaa1111")
    env.setdefault("FAKE_COMPARE_HASH", "bbb2222")
    if extra_env:
        env.update(extra_env)

    if cwd is not None:
        return subprocess.run(
            ["zsh", "-c", f'source "{GH_ALIASES}"; source "{GIT_FILTER}"; source "{GITHUB_FILTER}"; {snippet}'],
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_repo(tmpdir, remote_url)
        return subprocess.run(
            ["zsh", "-c", f'source "{GH_ALIASES}"; source "{GIT_FILTER}"; source "{GITHUB_FILTER}"; {snippet}'],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env,
        )


class GhCompareUrlBuildTest(unittest.TestCase):
    """_gh_compare_url_build のURL正規化と異常系を検証する。"""

    def test_ssh_remote_is_normalized_to_https(self):
        result = run_zsh("_gh_compare_url_build A B")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "https://github.com/owner/repo/compare/A...B"
        )

    def test_https_remote_passes_through(self):
        result = run_zsh(
            "_gh_compare_url_build A B", remote_url="https://github.com/owner/repo.git"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "https://github.com/owner/repo/compare/A...B"
        )

    def test_ssh_host_alias_is_normalized_to_github_com(self):
        # ~/.ssh/config のホストエイリアス(github-personal等)を使うremoteでも
        # github.comのURLへ変換されること。従来のgit@github.com:固定sedでは
        # 未変換のまま "git@github-personal:owner/repo/compare/..." を開いていた
        result = run_zsh(
            "_gh_compare_url_build A B", remote_url="git@github-personal:owner/repo.git"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "https://github.com/owner/repo/compare/A...B"
        )

    def test_ssh_protocol_url_is_normalized(self):
        result = run_zsh(
            "_gh_compare_url_build A B",
            remote_url="ssh://git@github.com/owner/repo.git",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "https://github.com/owner/repo/compare/A...B"
        )

    def test_non_github_remote_fails_without_url(self):
        # GitHub以外のホストのHTTPS remoteは変換対象外。誤ったcompare urlを開かないこと
        result = run_zsh(
            "_gh_compare_url_build A B", remote_url="https://gitlab.com/owner/repo.git"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("/compare/", result.stdout)

    def test_wrong_argument_count_fails(self):
        result = run_zsh("_gh_compare_url_build A")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)
        self.assertNotIn("https://", result.stdout)

    def test_missing_origin_remote_fails_without_url(self):
        # remote未登録時にgit remote get-urlが失敗する。
        # 従来は無検査で不正なURLを組み立ててopenへ渡していたため、その非回帰確認
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir, None)
            result = run_zsh("_gh_compare_url_build A B", cwd=tmpdir)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("https://", result.stdout)

    def test_gh_compare_url_opens_built_url(self):
        result = run_zsh(f"{FAKE_PICKERS}\ngh_compare_url A B")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OPEN https://github.com/owner/repo/compare/A...B", result.stderr)


class FghCompareTest(unittest.TestCase):
    """fgh-compare の3段選択・base以降絞り・キャンセル経路を検証する。"""

    def test_all_stages_selected_opens_compare_url(self):
        result = run_zsh(f"{FAKE_PICKERS}\nfgh-compare")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "OPEN https://github.com/owner/repo/compare/aaa1111...bbb2222", result.stderr
        )

    def test_compare_stage_receives_base_range_scoped_to_branch(self):
        # compare候補を「同じブランチかつbaseより後」に絞る実装をピン留めする。
        # range引数が "<base>..<branch>" でなくなるとbase以前のコミットも候補に混ざる
        result = run_zsh(f"{FAKE_PICKERS}\nfgh-compare")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SELECT_COMMIT header=compare元", result.stderr)
        self.assertIn("rev=main", result.stderr)
        self.assertIn("SELECT_RANGE header=compare先", result.stderr)
        self.assertIn("range=aaa1111..main", result.stderr)

    def test_compare_stage_does_not_use_single_revision_picker(self):
        # _select_commit_hash はブランチ引数を`git rev-parse --verify`で検証し、
        # --verifyは単一revision専用でA..B形式が必ず失敗する。
        # compare段をそちらへ戻すとレンジ絞り込みが常に「ブランチが見つかりません」で死ぬため、
        # レンジ用の別ピッカーを使い続けることを固定する
        result = run_zsh(f"{FAKE_PICKERS}\nfgh-compare")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("rev=aaa1111..main", result.stderr)

    def test_branch_cancel_skips_commit_selection_and_open(self):
        result = run_zsh(f"{FAKE_PICKERS}\nfgh-compare", extra_env={"FAKE_BRANCH": ""})
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("SELECT_COMMIT", result.stderr)
        self.assertNotIn("OPEN", result.stderr)

    def test_base_cancel_skips_open(self):
        result = run_zsh(
            f"{FAKE_PICKERS}\nfgh-compare", extra_env={"FAKE_BASE_HASH": ""}
        )
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("OPEN", result.stderr)

    def test_compare_cancel_skips_open(self):
        result = run_zsh(
            f"{FAKE_PICKERS}\nfgh-compare", extra_env={"FAKE_COMPARE_HASH": ""}
        )
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("OPEN", result.stderr)

    def test_outside_git_repository_fails_before_pickers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_zsh(f"{FAKE_PICKERS}\nfgh-compare", cwd=tmpdir)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("BR_ORG", result.stderr)
        self.assertNotIn("OPEN", result.stderr)


class SelectCommitHashInRangeTest(unittest.TestCase):
    """_select_commit_hash_in_range が実gitのA..Bレンジを扱えることを検証する。"""

    @staticmethod
    def _repo_with_commits(path, count):
        env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL="/dev/null",
            GIT_CONFIG_SYSTEM="/dev/null",
            GIT_AUTHOR_NAME="tester",
            GIT_AUTHOR_EMAIL="tester@example.com",
            GIT_COMMITTER_NAME="tester",
            GIT_COMMITTER_EMAIL="tester@example.com",
        )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, env=env, check=True)
        for i in range(count):
            subprocess.run(
                ["git", "commit", "-q", "--allow-empty", "-m", f"commit {i}"],
                cwd=path,
                env=env,
                check=True,
            )
        return env

    # filterはリストの1行目を選ぶだけのfakeにし、fzfの対話起動を避ける
    FAKE_FILTER = '''
EXIT_CODE_SIGINT=130
filter() {
    head -1
}
'''

    def test_range_excludes_base_and_earlier_commits(self):
        # git logのA..Bレンジがそのまま通ること（--verifyを介さない実装であることの実証）。
        # base=HEAD~2 のとき候補はHEAD~1とHEADの2件で、baseとそれ以前は含まれない
        with tempfile.TemporaryDirectory() as tmpdir:
            env = self._repo_with_commits(tmpdir, 4)
            hashes = subprocess.run(
                ["git", "log", "--pretty=format:%h", "-4"],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
            base = hashes[2]
            result = run_zsh(
                f'{self.FAKE_FILTER}\n_select_commit_hash_in_range "compare先" "{base}..main" 200',
                cwd=tmpdir,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            # filterが先頭行(最新コミット)を選ぶため、返るのはHEADのハッシュ
            self.assertEqual(result.stdout.strip(), hashes[0])
            self.assertNotEqual(result.stdout.strip(), base)

    def test_empty_range_returns_sigint(self):
        # baseがブランチ最新の場合は候補ゼロ。キャンセル扱いで抜ける
        with tempfile.TemporaryDirectory() as tmpdir:
            self._repo_with_commits(tmpdir, 2)
            result = run_zsh(
                f'{self.FAKE_FILTER}\n_select_commit_hash_in_range "compare先" "main..main" 200',
                cwd=tmpdir,
            )
            self.assertEqual(result.returncode, 130)
            self.assertIn("コミットが見つかりませんでした", result.stderr)

    def test_invalid_range_returns_sigint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._repo_with_commits(tmpdir, 2)
            result = run_zsh(
                f'{self.FAKE_FILTER}\n_select_commit_hash_in_range "compare先" "no-such-ref-xyz..main" 200',
                cwd=tmpdir,
            )
            self.assertEqual(result.returncode, 130)

    def test_filter_cancel_returns_sigint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = self._repo_with_commits(tmpdir, 3)
            base = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD~2"],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            result = run_zsh(
                'EXIT_CODE_SIGINT=130\nfilter() { :; }\n'
                f'_select_commit_hash_in_range "compare先" "{base}..main" 200',
                cwd=tmpdir,
            )
            self.assertEqual(result.returncode, 130)


if __name__ == "__main__":
    unittest.main()
