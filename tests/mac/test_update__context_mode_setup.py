import json
import unittest
from pathlib import Path


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


from support import REPO_ROOT


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
                "setup_claude_rtk",
                "setup_claude_genshijin",
                "setup_claude_superpowers",
                "setup_claude_mem",
                "setup_claude_dig",
                "setup_claude_example_skills",
            ),
            "mac/scripts/ai/gemini.sh": (
                "setup_gemini_context_mode",
                "setup_gemini_rtk",
                "setup_gemini_superpowers",
                "setup_gemini_claude_mem",
            ),
            "mac/scripts/ai/codex.sh": (
                "setup_codex_context_mode",
                "setup_codex_rtk",
                "setup_codex_superpowers",
                "setup_codex_claude_mem",
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
                (
                    "setup_claude_superpowers",
                    "setup_claude_context_mode",
                    "setup_claude_rtk",
                    "setup_claude_genshijin",
                    "setup_claude_dig",
                    "setup_claude_example_skills",
                    "setup_claude_mem",
                ),
            ),
            "mac/updates/claude.sh": (
                'source "${Repo}mac/scripts/ai/claude.sh"',
                (
                    "setup_claude_superpowers",
                    "setup_claude_context_mode",
                    "setup_claude_rtk",
                    "setup_claude_genshijin",
                    "setup_claude_dig",
                    "setup_claude_example_skills",
                    "setup_claude_mem",
                ),
            ),
            "mac/initialization/ai/gemini.sh": (
                'source "${Repo}mac/scripts/ai/gemini.sh"',
                ("setup_gemini_superpowers", "setup_gemini_context_mode", "setup_gemini_rtk", "setup_gemini_claude_mem"),
            ),
            "mac/updates/gemini.sh": (
                'source "${Repo}mac/scripts/ai/gemini.sh"',
                ("setup_gemini_superpowers", "setup_gemini_context_mode", "setup_gemini_rtk", "setup_gemini_claude_mem"),
            ),
            "mac/initialization/ai/codex.sh": (
                'source "${Repo}mac/scripts/ai/codex.sh"',
                ("setup_codex_superpowers", "setup_codex_context_mode", "setup_codex_rtk", "setup_codex_claude_mem"),
            ),
            "mac/updates/codex.sh": (
                'source "${Repo}mac/scripts/ai/codex.sh"',
                ("setup_codex_superpowers", "setup_codex_context_mode", "setup_codex_rtk", "setup_codex_claude_mem"),
            ),
        }

        for script_path, (source_line, call_lines) in expected_sources.items():
            self.assert_source_before_call(script_path, source_line, call_lines)

    def test_claude_genshijin_uses_upstream_marketplace(self):
        script = read_text("mac/scripts/ai/claude.sh")
        settings = json.loads(read_text("ai/claude/settings.json"))

        self.assertIn("function setup_claude_genshijin()", script)
        self.assertIn("claude plugin marketplace add InterfaceX-co-jp/genshijin", script)
        self.assertIn("claude plugin marketplace update genshijin", script)
        self.assertIn("genshijin@genshijin", script)
        self.assertTrue(settings["enabledPlugins"]["genshijin@genshijin"])
        self.assertEqual(
            settings["extraKnownMarketplaces"]["genshijin"],
            {
                "source": {
                    "repo": "InterfaceX-co-jp/genshijin",
                    "source": "github",
                }
            },
        )

        # The upstream marketplace declares its registered name as genshijin,
        # so repository slugs must not replace plugin or update identifiers.
        self.assertNotIn("genshijin@InterfaceX-co-jp/genshijin", script)

    def test_assistant_setup_scripts_source_shared_claude_mem_helpers(self):
        for script_path in (
            "mac/scripts/ai/claude.sh",
            "mac/scripts/ai/codex.sh",
            "mac/scripts/ai/gemini.sh",
        ):
            with self.subTest(script=script_path):
                self.assertIn(
                    'source "${Repo}mac/scripts/ai/claude_mem.sh"',
                    read_text(script_path),
                )

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

    def test_claude_settings_register_dig_plugin(self):
        settings = json.loads(read_text("ai/claude/settings.json"))

        self.assertTrue(settings["enabledPlugins"]["dig@kuu-marketplace"])
        self.assertEqual(
            settings["extraKnownMarketplaces"]["kuu-marketplace"],
            {
                "source": {
                    "repo": "fumiya-kume/claude-code",
                    "source": "github",
                }
            },
        )

    def test_claude_settings_register_example_skills_plugin(self):
        settings = json.loads(read_text("ai/claude/settings.json"))

        self.assertTrue(settings["enabledPlugins"]["example-skills@anthropic-agent-skills"])
        self.assertEqual(
            settings["extraKnownMarketplaces"]["anthropic-agent-skills"],
            {
                "source": {
                    "repo": "anthropics/skills",
                    "source": "github",
                }
            },
        )

        # skill-creator は example-skills プラグイン経由で提供される。
        # 同梱される他11スキルはトークン消費を避けるため skillOverrides で無効化する
        # (skill-creator 自体は off にしない)。
        override_off_skills = (
            "algorithmic-art",
            "brand-guidelines",
            "canvas-design",
            "doc-coauthoring",
            "frontend-design",
            "internal-comms",
            "mcp-builder",
            "slack-gif-creator",
            "theme-factory",
            "web-artifacts-builder",
            "webapp-testing",
        )
        for skill_name in override_off_skills:
            with self.subTest(skill=skill_name):
                self.assertEqual(settings["skillOverrides"][skill_name], "off")

        self.assertNotIn("skill-creator", settings["skillOverrides"])

    def test_claude_example_skills_setup_uses_marketplace_name_not_repo_name(self):
        script = read_text("mac/scripts/ai/claude.sh")

        self.assertIn("function setup_claude_example_skills()", script)
        self.assertIn("claude plugin marketplace add anthropics/skills", script)
        self.assertIn("claude plugin marketplace update anthropic-agent-skills", script)
        self.assertIn("example-skills@anthropic-agent-skills", script)
        # marketplace名(anthropic-agent-skills)とrepo名(anthropics/skills)が不一致であるため、
        # repo名をplugin ID/marketplace参照に誤用していないことを確認する
        self.assertNotIn("example-skills@anthropics/skills", script)
        self.assertNotIn("claude plugin marketplace update anthropics/skills", script)

    def test_claude_dig_setup_uses_marketplace_name_not_repo_name(self):
        script = read_text("mac/scripts/ai/claude.sh")

        self.assertIn("function setup_claude_dig()", script)
        self.assertIn("claude plugin marketplace add fumiya-kume/claude-code", script)
        self.assertIn("claude plugin marketplace update kuu-marketplace", script)
        self.assertIn("dig@kuu-marketplace", script)
        # repo名をmarketplace IDとして使う誤り(参考記事の誤記)を防ぐ
        self.assertNotIn("dig@fumiya-kume/claude-code", script)
        self.assertNotIn("claude plugin marketplace update fumiya-kume/claude-code", script)

    def test_claude_mem_setup_uses_noninteractive_worker_install_and_repair(self):
        script = read_text("mac/scripts/ai/claude_mem.sh")
        claude_script = read_text("mac/scripts/ai/claude.sh")

        self.assertIn("function setup_claude_mem_for_ide()", script)
        self.assertIn("function setup_claude_mem_runtime()", script)
        self.assertIn("function setup_claude_mem()", claude_script)

        for command_name in ("node", "npm", "uv", "bun"):
            with self.subTest(command=command_name):
                self.assertIn(f"require_ai_setup_command {command_name}", script)

        for expected in (
            "npx --yes claude-mem@latest install",
            "--ide",
            "--provider",
            '"${CLAUDE_MEM_PROVIDER:-claude}"',
            "--runtime",
            '"${CLAUDE_MEM_RUNTIME:-worker}"',
            "npx --yes claude-mem@latest repair",
            "npx --yes claude-mem@latest start",
            "npx --yes claude-mem@latest status",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, script)

        self.assertIn('setup_claude_mem_for_ide claude-code', claude_script)
        self.assertIn("claude plugin marketplace update thedotmack", claude_script)
        self.assertEqual(2, script.count("< /dev/null || return 1"))

    def test_codex_and_gemini_claude_mem_setup_use_supported_ide_ids(self):
        codex = read_text("mac/scripts/ai/codex.sh")
        gemini = read_text("mac/scripts/ai/gemini.sh")

        self.assertIn("function setup_codex_claude_mem()", codex)
        self.assertIn("setup_claude_mem_for_ide codex-cli", codex)
        self.assertIn("setup_claude_mem_runtime", codex)

        self.assertIn("function setup_gemini_claude_mem()", gemini)
        self.assertIn("setup_claude_mem_for_ide gemini-cli", gemini)
        self.assertIn("setup_claude_mem_runtime", gemini)


if __name__ == "__main__":
    unittest.main()
