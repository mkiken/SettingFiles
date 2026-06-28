import json
import unittest
from pathlib import Path


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class ContextModeSetupTest(unittest.TestCase):
    def test_common_setup_functions_are_defined(self):
        common = read_text("mac/scripts/common.sh")

        for function_name in (
            "require_context_mode_node",
            "setup_context_mode_cli",
            "setup_claude_context_mode",
            "setup_gemini_context_mode",
            "setup_codex_context_mode",
        ):
            self.assertIn(f"function {function_name}()", common)

    def test_ai_setup_and_update_scripts_call_context_mode_setup(self):
        expected_calls = {
            "mac/initialization/ai/claude.sh": "setup_claude_context_mode",
            "mac/updates/claude.sh": "setup_claude_context_mode",
            "mac/initialization/ai/gemini.sh": "setup_gemini_context_mode",
            "mac/updates/gemini.sh": "setup_gemini_context_mode",
            "mac/initialization/ai/codex.sh": "setup_codex_context_mode",
            "mac/updates/codex.sh": "setup_codex_context_mode",
        }

        for script_path, call in expected_calls.items():
            with self.subTest(script=script_path):
                self.assertIn(call, read_text(script_path))

    def test_context_mode_functions_apply_local_settings(self):
        common = read_text("mac/scripts/common.sh")

        self.assertIn(
            'smart_merge_json "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json',
            common,
        )
        self.assertIn(
            'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml',
            common,
        )

    def test_gemini_settings_register_context_mode_mcp_and_hooks(self):
        settings = json.loads(read_text("ai/gemini/settings.json"))

        self.assertEqual(
            settings["mcpServers"]["context-mode"],
            {"command": "context-mode"},
        )

        expected_hooks = {
            "BeforeTool": "context-mode hook gemini-cli beforetool",
            "AfterTool": "context-mode hook gemini-cli aftertool",
            "AfterModel": "context-mode hook gemini-cli aftermodel",
            "PreCompress": "context-mode hook gemini-cli precompress",
            "SessionStart": "context-mode hook gemini-cli sessionstart",
        }
        hooks = settings["hooks"]

        for event_name, command in expected_hooks.items():
            with self.subTest(event=event_name):
                event_hooks = hooks[event_name]
                self.assertTrue(
                    any(
                        hook["type"] == "command" and hook["command"] == command
                        for group in event_hooks
                        for hook in group["hooks"]
                    )
                )

        before_tool_matchers = [
            group["matcher"]
            for group in hooks["BeforeTool"]
            for hook in group["hooks"]
            if hook["command"] == "context-mode hook gemini-cli beforetool"
        ]
        self.assertIn(
            "run_shell_command|read_file|read_many_files|grep_search|search_file_content|web_fetch|activate_skill|mcp__plugin_context-mode",
            before_tool_matchers,
        )

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_codex_config_enables_context_mode_plugin_hooks(self):
        config = tomllib.loads(read_text("ai/codex/config.toml"))

        self.assertTrue(config["features"]["hooks"])
        self.assertTrue(config["features"]["plugin_hooks"])


if __name__ == "__main__":
    unittest.main()
