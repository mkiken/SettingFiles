import json
import re
import unittest

from support import REPO_ROOT


SETTINGS_PATH = REPO_ROOT / "ai/claude/settings.json"
MOD_DIR = REPO_ROOT / "ai/claude/mods/slash-anywhere"
HOME_PREFIX = "~/Desktop/repository/SettingFiles/"


class SlashAnywhereModTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        cls.register = (MOD_DIR / "hooks/register.ts").read_text(encoding="utf-8")

    def test_settings_load_the_mod_folder_through_plugin_dirs(self):
        value = self.settings["env"]["CLAUDE_CODE_PLUGIN_DIRS"]

        self.assertIn(HOME_PREFIX + "ai/claude/mods/slash-anywhere", value.split(":"))
        self.assertNotIn("/Users/", value)

    def test_plugin_dirs_target_is_a_mod_with_its_hooks_module(self):
        target = MOD_DIR
        manifest = json.loads(
            (target / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
        )
        hooks = json.loads((target / "hooks/hooks.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "slash-anywhere")
        self.assertEqual(hooks["modules"], ["./register.ts"])
        for module in hooks["modules"]:
            with self.subTest(module=module):
                self.assertTrue((target / "hooks" / module).is_file())

    def test_mod_hooks_only_the_autocomplete_event(self):
        # Hooking any event that shapes what the model receives would change
        # token use or break prompt caching; autocomplete is a typeahead-only UI event.
        hooked = set(re.findall(r"on\(\s*'([^']+)'", self.register))

        self.assertEqual(hooked, {"prompt.autocomplete"})

    def test_mod_registers_nothing_the_model_could_list(self):
        # Registered tools, commands and agents enter the system prompt listings.
        for forbidden in ("$.tool.register", "$.command.register", "$.agent", "$.model"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.register)

    def test_engine_generated_files_are_gitignored(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertIn("ai/claude/mods/*/tsconfig.json", gitignore)
        self.assertIn("ai/claude/mods/*/.claude-plugin/types/", gitignore)


if __name__ == "__main__":
    unittest.main()
