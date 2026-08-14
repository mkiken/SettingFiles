import unittest

from support import REPO_ROOT


CORE = REPO_ROOT / "ai/common/pr_comment_implement_core.md"


class PrCommentImplementFinalActionSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

    def test_code_change_options_expose_all_four_final_states(self):
        for option in (
            'add "コミット & 親ブランチにマージ & push"',
            'add "コミット & 親ブランチにマージ"',
            'add "コミットのみ"',
            'always add "コミットしない"',
        ):
            with self.subTest(option=option):
                self.assertIn(option, self.content)

        for compound_option in (
            'add "コミット & 親ブランチにマージ & push & 返信 & resolve"',
            'add "コミット & 親ブランチにマージ & push & 返信"',
        ):
            with self.subTest(compound_option=compound_option):
                self.assertIn(compound_option, self.content)

    def test_option_limit_preserves_every_executable_action(self):
        for contract in (
            "only when it can display every",
            "plain-text ordered list of every option",
            "Never omit or group executable options",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.content)

    def test_commit_only_stops_before_merge(self):
        commit_only = self.content.index("If the selection was `コミットのみ`")
        merge = self.content.index("#### Merge the task branch back into the PR head")

        self.assertLess(commit_only, merge)
        self.assertIn("do not merge or push", self.content[commit_only:merge])
        self.assertIn("`TASK_PATH` and `TASK_BRANCH` as preserved", self.content[commit_only:merge])

    def test_local_merge_stops_after_cleanup_and_before_push(self):
        cleanup = self.content.index("Once cleanup is verified")
        local_merge = self.content.index(
            "If the selection was `コミット & 親ブランチにマージ`"
        )
        push = self.content.index("#### Push, handling a racing remote")

        self.assertLess(cleanup, local_merge)
        self.assertLess(local_merge, push)
        local_merge_contract = self.content[local_merge:push]
        self.assertIn("skip fetch, push, reply, and resolve", local_merge_contract)
        self.assertIn("Leave the 🚀 reaction in place", local_merge_contract)

    def test_push_section_is_limited_to_push_actions(self):
        push = self.content.index("#### Push, handling a racing remote")
        push_contract = self.content[push:]

        self.assertIn(
            "Run this section only when the selected action contains `& push`",
            push_contract,
        )
        self.assertIn("Never force-push", push_contract)
        self.assertIn("require its object ID to equal the pushed commit", push_contract)

    def test_push_race_refreshes_the_tracking_ref(self):
        fetch_command = (
            'git fetch origin "+refs/heads/${HEAD_BRANCH}:'
            'refs/remotes/origin/${HEAD_BRANCH}"'
        )

        self.assertEqual(self.content.count(fetch_command), 2)

        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(codex_skill.count(fetch_command), 2)

    def test_platform_adapters_receive_the_shared_contract(self):
        claude_skill = (
            REPO_ROOT / "ai/claude/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")
        gemini_command = (
            REPO_ROOT / "ai/gemini/commands/pr-comment-implement.toml"
        ).read_text(encoding="utf-8")
        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("~/.claude/common/pr_comment_implement_core.md", claude_skill)
        self.assertIn("~/.gemini/common/pr_comment_implement_core.md", gemini_command)
        self.assertIn('add "コミット & 親ブランチにマージ"', codex_skill)
        self.assertIn("plain-text ordered list of every option", codex_skill)


if __name__ == "__main__":
    unittest.main()
