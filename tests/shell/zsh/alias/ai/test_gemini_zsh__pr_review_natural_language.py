import subprocess
import unittest

from support import REPO_ROOT

AI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"
GEMINI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/gemini.zsh"


def run_gm_pr_review(fn_and_args: str) -> subprocess.CompletedProcess:
    """gm-pr-review系はgmh(=gmp=gm)を最終的に呼ぶ。実起動を避けるため、gemini.zsh
    ソース後に末端の gm を差し替えて `-i` の最終引数だけをstdoutへ出す
    （先にスタブすると gemini.zsh 自身の gm 再定義で上書きされる）。"""
    script = f'''
source "{AI_ZSH}"
source "{GEMINI_ZSH}"
gm() {{
    printf '%s' "${{@[-1]}}"
}}
{fn_and_args}
'''
    return subprocess.run(["zsh", "-c", script], capture_output=True, text=True)


class GmPrReviewNaturalLanguageTest(unittest.TestCase):
    """gemini-cliの既知のレース（カスタムコマンドの非同期ロード中に初期プロンプトが
    処理されうる）でスラッシュコマンド展開が失敗しても、起動文字列が文章として意味
    が通るようにするための形をピン留めする。"""

    def test_starts_with_slash_pr_review_and_pr_number(self):
        result = run_gm_pr_review("gm-pr-review 3409")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            result.stdout.startswith("/pr-review 3409"),
            result.stdout,
        )

    def test_pr_number_reappears_in_natural_language_tail(self):
        # 未展開時にモデルが raw 文字列だけからPR番号を読めるようにする
        result = run_gm_pr_review("gm-pr-review 3409")
        tail = result.stdout[len("/pr-review 3409"):]
        self.assertIn("3409", tail)

    def test_does_not_start_with_comment_or_block_comment_markers(self):
        # gemini-cli の isSlashCommand は `//` や `/*` を除外する — この形を壊さない
        result = run_gm_pr_review("gm-pr-review 3409")
        self.assertFalse(result.stdout.startswith("//"))
        self.assertFalse(result.stdout.startswith("/*"))

    def test_additional_instructions_precede_failsafe_note(self):
        result = run_gm_pr_review("gm-pr-review 3409 セキュリティ重点")
        self.assertEqual(result.returncode, 0, result.stderr)
        instructions_pos = result.stdout.find("セキュリティ重点")
        failsafe_pos = result.stdout.find("Failsafe")
        self.assertGreater(instructions_pos, -1, result.stdout)
        self.assertGreater(failsafe_pos, -1, result.stdout)
        self.assertLess(
            instructions_pos,
            failsafe_pos,
            "追加指示はフェイルセーフ括弧より前に来る必要がある（tomlの先頭トークン=PR番号、"
            "残り=追加指示というパースを壊さないため）",
        )

    def test_subagents_variant_has_same_shape(self):
        result = run_gm_pr_review("gm-pr-review-subagent 3409")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("/pr-review-subagents 3409"), result.stdout)
        self.assertIn("3409", result.stdout[len("/pr-review-subagents 3409"):])

    def test_failsafe_note_avoids_shell_metacharacters(self):
        # 否定ピン: フェイルセーフ文はgemini-cliの `{{args}}` 置換を経由し `!{}` の
        # 外で生の文字列として扱われる（ShellProcessor.processStringのescapeShellArgは
        # `!{...}` の中身にしか掛からない）。ここに !/$/` が混入すると、将来この文言が
        # 別の経路（シェル評価される場所）に転用された際の注入事故につながるため、
        # 未然に禁止しておく。
        result = run_gm_pr_review("gm-pr-review 3409")
        for forbidden in ("!", "$", "`"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, result.stdout)


if __name__ == "__main__":
    unittest.main()
