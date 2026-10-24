import json
import re
import unittest

from support import REPO_ROOT


SETTINGS_PATH = REPO_ROOT / "ai/claude/settings.json"
MOD_DIR = REPO_ROOT / "ai/claude/mods/rich-output"
HOME_PREFIX = "~/Desktop/repository/SettingFiles/"


class RichOutputModTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        cls.register = (MOD_DIR / "hooks/register.tsx").read_text(encoding="utf-8")

    def test_plugin_dirs_lists_every_mod_with_home_relative_paths(self):
        dirs = self.settings["env"]["CLAUDE_CODE_PLUGIN_DIRS"].split(":")

        self.assertEqual(
            dirs,
            [
                HOME_PREFIX + "ai/claude/mods/slash-anywhere",
                HOME_PREFIX + "ai/claude/mods/rich-output",
            ],
        )
        for entry in dirs:
            with self.subTest(entry=entry):
                self.assertNotIn("/Users/", entry)
                self.assertTrue((REPO_ROOT / entry.removeprefix(HOME_PREFIX)).is_dir())

    def test_mod_manifest_and_hooks_module_are_consistent(self):
        manifest = json.loads(
            (MOD_DIR / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
        )
        hooks = json.loads((MOD_DIR / "hooks/hooks.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "rich-output")
        self.assertEqual(hooks["modules"], ["./register.tsx"])
        self.assertTrue((MOD_DIR / "hooks/markdown.ts").is_file())
        self.assertTrue((MOD_DIR / "hooks/markdown.test.tsx").is_file())

    def test_mod_hooks_only_the_render_event(self):
        # Rendering never reaches the stored conversation; any other event could
        # change what the model receives and break prompt caching.
        hooked = set(re.findall(r"on\(\s*'([^']+)'", self.register))

        self.assertEqual(hooked, {"ui.render"})

    def test_mod_registers_nothing_the_model_could_list(self):
        for forbidden in ("$.tool.register", "$.command.register", "$.agent", "$.model"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.register)

    def test_non_terminal_surfaces_and_summaries_fall_through_to_the_engine(self):
        self.assertIn("e.surface !== 'terminal'", self.register)
        self.assertIn("e.props.isSummary", self.register)
        self.assertIn("e.props.isExpanded", self.register)


if __name__ == "__main__":
    unittest.main()
