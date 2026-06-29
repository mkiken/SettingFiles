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
    def assert_source_before_call(
        self,
        script_path: str,
        source_line: str,
        call_lines: tuple[str, ...],
    ) -> None:
        script = read_text(script_path)

        common_source_index = script.index('source "$(dirname "$0")/')
        assistant_source_index = script.index(source_line)
        self.assertGreater(assistant_source_index, common_source_index)

        for call_line in call_lines:
            with self.subTest(script=script_path, call=call_line):
                self.assertLess(assistant_source_index, script.index(call_line))

    def test_common_setup_does_not_source_assistant_specific_setup_files(self):
        common = read_text("mac/scripts/common.sh")

        for function_name in (
            "require_context_mode_node",
            "setup_context_mode_cli",
        ):
            self.assertIn(f"function {function_name}()", common)

        for assistant_name in ("claude", "gemini", "codex"):
            self.assertNotIn(f"mac/scripts/ai/{assistant_name}.sh", common)

        for function_name in (
            "setup_claude_context_mode",
            "setup_gemini_context_mode",
            "setup_codex_context_mode",
            "setup_claude_superpowers",
            "setup_gemini_superpowers",
            "setup_codex_superpowers",
        ):
            self.assertNotIn(f"function {function_name}()", common)

    def test_assistant_specific_setup_functions_are_defined_in_own_files(self):
        expected_functions = {
            "mac/scripts/ai/claude.sh": (
                "setup_claude_context_mode",
                "setup_claude_superpowers",
                "setup_claude_mem",
            ),
            "mac/scripts/ai/gemini.sh": (
                "setup_gemini_context_mode",
                "setup_gemini_superpowers",
            ),
            "mac/scripts/ai/codex.sh": (
                "setup_codex_context_mode",
                "setup_codex_superpowers",
            ),
        }

        for script_path, function_names in expected_functions.items():
            script = read_text(script_path)
            with self.subTest(script=script_path):
                for function_name in function_names:
                    self.assertIn(f"function {function_name}()", script)

    def test_ai_setup_and_update_scripts_source_assistant_setup_before_calls(self):
        expected_sources = {
            "mac/initialization/ai/claude.sh": (
                'source "${Repo}mac/scripts/ai/claude.sh"',
                ("setup_claude_superpowers", "setup_claude_context_mode", "setup_claude_mem"),
            ),
            "mac/updates/claude.sh": (
                'source "${Repo}mac/scripts/ai/claude.sh"',
                ("setup_claude_superpowers", "setup_claude_context_mode", "setup_claude_mem"),
            ),
            "mac/initialization/ai/gemini.sh": (
                'source "${Repo}mac/scripts/ai/gemini.sh"',
                ("setup_gemini_superpowers", "setup_gemini_context_mode"),
            ),
            "mac/updates/gemini.sh": (
                'source "${Repo}mac/scripts/ai/gemini.sh"',
                ("setup_gemini_superpowers", "setup_gemini_context_mode"),
            ),
            "mac/initialization/ai/codex.sh": (
                'source "${Repo}mac/scripts/ai/codex.sh"',
                ("setup_codex_superpowers", "setup_codex_context_mode"),
            ),
            "mac/updates/codex.sh": (
                'source "${Repo}mac/scripts/ai/codex.sh"',
                ("setup_codex_superpowers", "setup_codex_context_mode"),
            ),
        }

        for script_path, (source_line, call_lines) in expected_sources.items():
            self.assert_source_before_call(script_path, source_line, call_lines)

    def test_context_mode_functions_apply_local_settings(self):
        gemini = read_text("mac/scripts/ai/gemini.sh")
        codex = read_text("mac/scripts/ai/codex.sh")

        self.assertIn(
            'smart_merge_json "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json',
            gemini,
        )
        self.assertNotIn(
            'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml',
            codex,
        )

    def test_codex_setup_and_update_merge_config_once_after_setup_steps(self):
        merge_line = 'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml'
        expected_order = {
            "mac/initialization/ai/codex.sh": (
                "setup_codex_context_mode",
                "npm install -g @nogataka/ccresume-codex",
            ),
            "mac/updates/codex.sh": ("setup_codex_context_mode",),
        }

        for script_path, earlier_lines in expected_order.items():
            script = read_text(script_path)
            with self.subTest(script=script_path):
                self.assertEqual(script.count(merge_line), 1)

                merge_index = script.index(merge_line)
                for earlier_line in earlier_lines:
                    self.assertLess(script.index(earlier_line), merge_index)

                self.assertLess(merge_index, script.index("echo \"Codex"))

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

    def test_brewfile_installs_bun_for_claude_mem_runtime(self):
        brewfile = read_text("mac/Brewfile")

        self.assertIn('brew "bun"', brewfile)

    def test_claude_settings_register_claude_mem_plugin(self):
        settings = json.loads(read_text("ai/claude/settings.json"))

        self.assertTrue(settings["enabledPlugins"]["claude-mem@thedotmack"])
        self.assertEqual(
            settings["extraKnownMarketplaces"]["thedotmack"],
            {
                "source": {
                    "repo": "thedotmack/claude-mem",
                    "source": "github",
                }
            },
        )

    def test_claude_mem_setup_uses_noninteractive_worker_install_and_repair(self):
        script = read_text("mac/scripts/ai/claude.sh")

        self.assertIn("function setup_claude_mem()", script)

        for command_name in ("claude", "jq", "node", "npm", "uv", "bun"):
            with self.subTest(command=command_name):
                self.assertIn(f"require_ai_setup_command {command_name}", script)

        for expected in (
            "npx --yes claude-mem@latest install",
            "--ide",
            "claude-code",
            "--provider",
            '"${CLAUDE_MEM_PROVIDER:-claude}"',
            "--runtime",
            '"${CLAUDE_MEM_RUNTIME:-worker}"',
            "npx --yes claude-mem@latest repair",
            "claude plugin marketplace update thedotmack",
            "npx --yes claude-mem@latest start",
            "npx --yes claude-mem@latest status",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, script)


if __name__ == "__main__":
    unittest.main()
