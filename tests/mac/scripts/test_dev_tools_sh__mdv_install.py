import json
import unittest

from support import REPO_ROOT


GO_INSTALL = "go install github.com/gr1m0h/mdv@latest"

DEV_TOOLS_PATH = REPO_ROOT / "mac/initialization/dev_tools.sh"
UPDATE_PATH = REPO_ROOT / "mac/update"
MANAGED_ZSH_PATH = REPO_ROOT / "shell/zsh/managed.zsh"
CLAUDE_SETTINGS_PATH = REPO_ROOT / "ai/claude/settings.json"

# mdts の痕跡を探す対象。tmux/herdr のテストは "mdts-plan-single-file-review" を
# 「スペース無しハイフンスラッグ」の文字列例として使うだけでツールとは無関係なので
# 走査対象から外し、誤検出を防ぐ。
MDTS_FREE_FILES = (
    "mac/initialization/dev_tools.sh",
    "mac/update",
    "mac/initialization/NOTES.md",
    "ai/claude/settings.json",
    "ai/common/prompt_base.md",
    "ai/codex/codex_base.md",
    "ai/claude/_CLAUDE.md",
    "ai/codex/_AGENTS.md",
)

DELETED_MDTS_ASSETS = (
    "mac/scripts/mdts.sh",
    "mac/updates/mdts.sh",
    "terminal/mdts",
)


class MdvInstallWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dev_tools = DEV_TOOLS_PATH.read_text(encoding="utf-8")
        cls.update = UPDATE_PATH.read_text(encoding="utf-8")
        cls.managed_zsh = MANAGED_ZSH_PATH.read_text(encoding="utf-8")

    def test_dev_tools_installs_mdv_via_go_install(self):
        self.assertEqual(self.dev_tools.count(GO_INSTALL), 1)

    def test_update_installs_mdv_after_ai_tools(self):
        self.assertEqual(self.update.count(GO_INSTALL), 1)
        codex_update = self.update.index("updates/codex.sh")
        self.assertGreater(self.update.index(GO_INSTALL), codex_update)

    def test_no_mdts_references_remain(self):
        for relative in MDTS_FREE_FILES:
            with self.subTest(path=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("mdts", text)

    def test_mdts_assets_are_deleted(self):
        for relative in DELETED_MDTS_ASSETS:
            with self.subTest(path=relative):
                self.assertFalse((REPO_ROOT / relative).exists())

    def test_mdv_css_is_exported_from_managed_zsh(self):
        self.assertIn(
            'export MDV_CSS="${SET}terminal/mdv/mdv-plans.css"', self.managed_zsh
        )
        # go install したバイナリが PATH に載ってから環境変数を渡す順序を保つ
        go_bin = self.managed_zsh.index("$HOME/go/bin")
        self.assertGreater(self.managed_zsh.index("export MDV_CSS="), go_bin)

    def test_mdv_css_target_exists(self):
        self.assertTrue((REPO_ROOT / "terminal/mdv/mdv-plans.css").is_file())

    def test_claude_settings_allows_mdv_in_alphabetical_order(self):
        settings = json.loads(CLAUDE_SETTINGS_PATH.read_text(encoding="utf-8"))
        allow = settings["permissions"]["allow"]
        self.assertIn("Bash(mdv:*)", allow)
        self.assertNotIn("Bash(mdts:*)", allow)
        self.assertEqual(allow, sorted(allow))


if __name__ == "__main__":
    unittest.main()
