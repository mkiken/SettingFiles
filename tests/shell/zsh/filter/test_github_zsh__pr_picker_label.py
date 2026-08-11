import subprocess
import unittest

from support import REPO_ROOT

GH_ALIASES = REPO_ROOT / "shell/zsh/alias/gh.zsh"
GITHUB_FILTER = REPO_ROOT / "shell/zsh/filter/github.zsh"


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-c", f'source "{GH_ALIASES}"; source "{GITHUB_FILTER}"; {snippet}'],
        capture_output=True,
        text=True,
    )


# ghpl_branch(gh pr list呼び出し)とfilterをどちらもfakeへ差し替える。
# filterはargvをそのまま出力するだけにし、--promptの有無/内容だけを検証対象にする
FAKE_COMMANDS = '''
gh() {
    if [[ "$1 $2" == "pr list" ]]; then
        printf 'GH_CALL %s\\n' "$*" >&2
        printf '[]'
        return 0
    fi
    return 0
}
filter() {
    printf 'FILTER_ARGS %s\\n' "$*" >&2
}
'''


class FghSelectPrLabelTest(unittest.TestCase):
    """_fgh_select_pr / _fgh_select_pr_number の--label-prefix剥がしとghpl_branchへの転送を検証する。"""

    def test_label_prefix_becomes_fzf_prompt(self):
        result = run_zsh(f'{FAKE_COMMANDS}\n_fgh_select_pr --label-prefix review-subagents')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prompt review-subagents ", result.stderr)

    def test_no_label_prefix_keeps_default_prompt_unset(self):
        # 既存呼び出し元（fghpl_branch等）の表示を変えないための非回帰確認:
        # --label-prefix未指定時は--promptを一切付与しない(fzf既定の"> "のまま)
        result = run_zsh(f'{FAKE_COMMANDS}\n_fgh_select_pr')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--prompt", result.stderr)

    def test_label_prefix_is_stripped_before_reaching_ghpl_branch(self):
        # --label-prefixはghpl_branch（gh pr listのクエリフラグ経由）へ渡ってはならない
        result = run_zsh(f'{FAKE_COMMANDS}\n_fgh_select_pr --label-prefix review')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--label-prefix", result.stderr.split("GH_CALL", 1)[-1])

    def test_author_query_flag_still_forwarded_without_label_prefix(self):
        # 既存呼び出し元の非回帰: _fgh_select_pr_number --author "@me"（github.zsh内で使用）は
        # 従来どおりghpl_branch経由でgh pr listへ届くこと
        result = run_zsh(f'{FAKE_COMMANDS}\n_fgh_select_pr_number --author "@me"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--author @me", result.stderr)
        self.assertNotIn("--prompt", result.stderr)

    def test_label_prefix_with_author_query_flag_forwards_both(self):
        # --label-prefixとクエリフラグを両方渡すケース（freview経由では発生しないが、
        # 将来の呼び出し元がPRピッカーへラベルを付けつつ検索条件も渡せることの確認）
        result = run_zsh(
            f'{FAKE_COMMANDS}\n_fgh_select_pr_number --label-prefix review --author "@me"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prompt review ", result.stderr)
        self.assertIn("--author @me", result.stderr)


if __name__ == "__main__":
    unittest.main()
