import unittest
from pathlib import Path


from support import REPO_ROOT


class GenerateCodexAgentsSyncTest(unittest.TestCase):
    """generate_codex_agents: ai/codex/_AGENTS.md が prompt_base.md と
    codex_base.md の単純連結と一致することを保証する。

    prompt_base.md（常時読み込み層）を編集して generate_codex_agents の再実行を
    忘れると、Codex だけ古い指示で静かに動き続ける。この回帰をコミット前の
    `unittest discover` で検出する。generate_codex_agents 関数自体は
    ai/codex/_AGENTS.md を直接上書きする副作用を持つため、ここでは呼び出さず
    元となる2ファイルの単純連結（関数の実装と同じ順序: prompt_base + 空行 +
    codex_base）を Python 側で
    再現し、コミット済み _AGENTS.md と突き合わせる。
    """

    def test_committed_agents_md_matches_concatenation_of_sources(self):
        prompt_base = (REPO_ROOT / "ai/common/prompt_base.md").read_text(encoding="utf-8")
        codex_base = (REPO_ROOT / "ai/codex/codex_base.md").read_text(encoding="utf-8")
        expected = f"{prompt_base}\n{codex_base}"

        committed = (REPO_ROOT / "ai/codex/_AGENTS.md").read_text(encoding="utf-8")

        self.assertEqual(
            committed,
            expected,
            "ai/codex/_AGENTS.md is stale — run "
            "`zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` "
            "after editing prompt_base.md / codex_base.md",
        )

        # Character text must not leak into Codex's active global guidance after
        # the style source moved to genshijin.
        self.assertNotIn("You are Nyaruko", committed)
        self.assertNotIn("原始人のように簡潔に返答せよ", committed)


if __name__ == "__main__":
    unittest.main()
