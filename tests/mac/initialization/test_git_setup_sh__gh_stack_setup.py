import unittest

from support import REPO_ROOT


class GhStackSetupTest(unittest.TestCase):
    def setUp(self):
        self.setup_sh = (REPO_ROOT / "mac/initialization/git_setup.sh").read_text(encoding="utf-8")

    def test_extension_is_installed(self):
        self.assertIn("gh extension install github/gh-stack", self.setup_sh)

    def test_skill_install_lines_use_user_scope_and_force(self):
        # --scope の既定は project でリポジトリ直下へ入ってしまうため user を明示する必要がある。
        # -f が無いと再実行時に対話プロンプトで初期化が止まる
        skill_lines = [
            line
            for line in self.setup_sh.splitlines()
            if "gh skill install github/gh-stack" in line
        ]
        self.assertTrue(skill_lines, "gh skill install github/gh-stack の行が見つからない")
        for line in skill_lines:
            self.assertIn("--scope user", line)
            self.assertIn("-f", line)

    def test_skill_is_installed_for_both_claude_code_and_codex(self):
        self.assertIn("--agent claude-code", self.setup_sh)
        self.assertIn("--agent codex", self.setup_sh)


class GhStackUpdateTest(unittest.TestCase):
    def setUp(self):
        self.update_sh = (REPO_ROOT / "mac/update").read_text(encoding="utf-8")

    def test_skill_update_targets_gh_stack_only(self):
        # 管理外のuser scope skill（caveman, kiro-*, harness-rating-report）を
        # 巻き込まないよう --all は使わない
        self.assertIn("gh skill update gh-stack", self.update_sh)
        skill_update_lines = [
            line for line in self.update_sh.splitlines() if line.strip().startswith("gh skill update")
        ]
        for line in skill_update_lines:
            self.assertNotIn("--all", line)

    def test_no_nonexistent_skill_upgrade_command(self):
        # gh skill にupgradeサブコマンドは存在しない。正しくは update
        self.assertNotIn("gh skill upgrade", self.update_sh)


if __name__ == "__main__":
    unittest.main()
