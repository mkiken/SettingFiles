import unittest
from pathlib import Path


from support import REPO_ROOT


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class GenshijinPromptIntegrationTest(unittest.TestCase):
    def test_shared_rule_contains_upstream_activation_contract(self):
        rule = read_text("ai/common/genshijin-activate.md")

        self.assertIn("原始人のように簡潔に返答せよ", rule)
        self.assertIn("原始人やめて", rule)
        self.assertIn("破壊的操作の確認", rule)

    def test_local_file_policy_overrides_upstream_confirmation(self):
        rule = read_text("ai/common/genshijin-activate.md")
        policy = read_text("ai/common/genshijin-file-policy.md")

        self.assertIn("genshijin口調で書くか", rule)
        self.assertIn("Do not ask whether to use genshijin style.", policy)
        self.assertIn("only when the user explicitly requests it for that file", policy)
        self.assertIn("Keep genshijin active for conversational responses.", policy)

    def test_active_entrypoints_use_genshijin_without_character_imports(self):
        claude = read_text("ai/claude/_CLAUDE.md")
        gemini = read_text("ai/gemini/_GEMINI.md")

        self.assertLess(
            claude.index("@../common/prompt_base.md"),
            claude.index("@../common/genshijin-file-policy.md"),
        )
        self.assertLess(
            gemini.index("@common/genshijin-activate.md"),
            gemini.index("@common/genshijin-file-policy.md"),
        )

        # Character files remain as an inactive palette, so active entrypoints
        # must not import them alongside the single genshijin style source.
        self.assertNotIn("characters/", claude)
        self.assertNotIn("characters/", gemini)

    def test_updates_sync_before_consuming_the_rule(self):
        codex_update = read_text("mac/updates/codex.sh")
        gemini_update = read_text("mac/updates/gemini.sh")

        self.assertNotIn("sync_genshijin_rule", codex_update)
        self.assertIn("sync_genshijin_rule", gemini_update)

    def test_sync_helper_protects_existing_rule_on_fetch_failure(self):
        common = read_text("mac/scripts/common.sh")

        self.assertIn("function sync_genshijin_rule()", common)
        self.assertIn("InterfaceX-co-jp/genshijin/main/rules/genshijin-activate.md", common)
        self.assertIn('curl -fsSL "$upstream_url" >"$tmp_file"', common)
        self.assertIn('/usr/bin/grep -Fq "原始人のように簡潔に返答せよ" "$tmp_file"', common)
        self.assertIn('cmp -s "$tmp_file" "$rule_path"', common)


if __name__ == "__main__":
    unittest.main()
