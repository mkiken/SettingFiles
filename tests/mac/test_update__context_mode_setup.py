import json
import subprocess
import tempfile
import unittest
from pathlib import Path


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


from support import REPO_ROOT, sanitized_env


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

        for assistant_name in ("claude", "gemini", "codex"):
            self.assertNotIn(f"mac/scripts/ai/{assistant_name}.sh", common)

        for function_name in (
            "setup_claude_superpowers",
            "setup_gemini_superpowers",
            "setup_codex_superpowers",
        ):
            self.assertNotIn(f"function {function_name}()", common)

    def test_assistant_specific_setup_functions_are_defined_in_own_files(self):
        expected_functions = {
            "mac/scripts/ai/claude.sh": (
                "setup_claude_rtk",
                "setup_claude_genshijin",
                "setup_claude_superpowers",

                "setup_claude_dig",
                "setup_claude_example_skills",
                "setup_claude_ponytail",
                "setup_claude_cache_tools",
            ),
            "mac/scripts/ai/gemini.sh": (
                "setup_gemini_rtk",
                "setup_gemini_superpowers",

            ),
            "mac/scripts/ai/codex.sh": (
                "setup_codex_rtk",
                "setup_codex_caveman",
                "update_codex_caveman",
                "setup_codex_superpowers",

                "setup_codex_ponytail",
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
                    "setup_claude_rtk",
                    "setup_claude_genshijin",
                    "setup_claude_dig",
                    "setup_claude_example_skills",

                    "setup_claude_ponytail",
                    "setup_claude_cache_tools",
                ),
            ),
            "mac/updates/claude.sh": (
                'source "${Repo}mac/scripts/ai/claude.sh"',
                (
                    "setup_claude_superpowers",
                    "setup_claude_rtk",
                    "setup_claude_genshijin",
                    "setup_claude_dig",
                    "setup_claude_example_skills",

                    "setup_claude_ponytail",
                    "setup_claude_cache_tools",
                ),
            ),
            "mac/initialization/ai/gemini.sh": (
                'source "${Repo}mac/scripts/ai/gemini.sh"',
                ("setup_gemini_superpowers", "setup_gemini_rtk"),
            ),
            "mac/updates/gemini.sh": (
                'source "${Repo}mac/scripts/ai/gemini.sh"',
                ("setup_gemini_superpowers", "setup_gemini_rtk"),
            ),
            "mac/initialization/ai/codex.sh": (
                'source "${Repo}mac/scripts/ai/codex.sh"',
                ("setup_codex_superpowers", "setup_codex_rtk", "setup_codex_caveman", "setup_codex_ponytail"),
            ),
            "mac/updates/codex.sh": (
                'source "${Repo}mac/scripts/ai/codex.sh"',
                ("setup_codex_superpowers", "setup_codex_rtk", "update_codex_caveman", "setup_codex_ponytail"),
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

    def test_ai_setup_does_not_reinstall_claude_mem(self):
        # Removing the integration must survive initialization and updates.
        for platform in ("claude", "codex", "gemini"):
            for directory in ("mac/scripts/ai", "mac/initialization/ai", "mac/updates"):
                with self.subTest(platform=platform, directory=directory):
                    self.assertNotIn("claude_mem", read_text(f"{directory}/{platform}.sh"))
        settings = json.loads(read_text("ai/claude/settings.json"))
        self.assertNotIn("claude-mem@thedotmack", settings["enabledPlugins"])
        self.assertNotIn("thedotmack", settings["extraKnownMarketplaces"])

    def test_gemini_update_merges_live_settings_into_repository_only(self):
        update = read_text("mac/updates/gemini.sh")
        merge_line = 'smart_merge_json ~/.gemini/settings.json "${Repo}ai/gemini/settings.json"'
        reverse_line = 'smart_merge_json "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json'

        self.assertEqual(update.count(merge_line), 1)
        # Updates capture live settings; initialization applies repository settings.
        self.assertNotIn(reverse_line, update)

    def test_codex_setup_and_update_merge_config_once_after_setup_steps(self):
        merge_line = 'smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml'
        expected_order = {
            "mac/initialization/ai/codex.sh": (
                "setup_codex_ponytail",
                "npm install -g @nogataka/ccresume-codex",
            ),
        }

        for script_path, earlier_lines in expected_order.items():
            script = read_text(script_path)
            with self.subTest(script=script_path):
                self.assertEqual(script.count(merge_line), 1)

                merge_index = script.index(merge_line)
                for earlier_line in earlier_lines:
                    self.assertLess(script.index(earlier_line), merge_index)

                self.assertLess(merge_index, script.index("echo \"Codex"))

        update = read_text("mac/updates/codex.sh")
        self.assertLess(update.index("setup_codex_ponytail"), update.index("sync_codex_config.py"))
        # Updates capture live settings; initialization applies repository settings.
        self.assertNotIn(merge_line, update)

    def test_codex_sync_excludes_local_state_and_preserves_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live.toml"
            repo = root / "repo.toml"
            live.write_text('model = "new"\nflag = true\ndates = [2026-11-12]\n[projects."/Users/testuser/project"]\ntrust_level = "trusted"\n'
                            '[hooks.state."/Users/testuser/hook"]\ntrusted_hash = "hash"\n'
                            '[tui]\nscreen_reader_detection_done = true\nstarted = 2026-11-12\n'
                            '[tui.model_availability_nux]\nmodel = 1\n'
                            '[plugins.example]\nenabled = true\n')
            repo.write_text('# Keep this comment\nmodel = "old" # Keep this too\nflag = 1\ndates = [2026-11-11]\n'
                            '[hooks.state."existing"]\ntrusted_hash = "original"\n')
            result = subprocess.run(
                ["uv", "run", "--no-project", "--script",
                 str(REPO_ROOT / "mac/scripts/ai/sync_codex_config.py"), str(live), str(repo),
                 str(REPO_ROOT / "shell/zsh/alias/utils.zsh")],
                env=sanitized_env({"HOME": directory, "XDG_STATE_HOME": directory,
                                   "SMART_MERGE_ACTION": "merge_src"}),
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            text = repo.read_text()
            config = tomllib.loads(text)
            self.assertEqual(config["model"], "new")
            self.assertIs(config["flag"], True)
            self.assertEqual([str(date) for date in config["dates"]], ["2026-11-11", "2026-11-12"])
            self.assertTrue(all(not isinstance(date, str) for date in config["dates"]))
            self.assertTrue(config["plugins"]["example"]["enabled"])
            self.assertFalse(isinstance(config["tui"]["started"], str))
            self.assertIn("# Keep this comment", text)
            self.assertIn("# Keep this too", text)
            # Machine-specific trust and UI state must not enter the repository.
            self.assertNotIn("projects", config)
            self.assertEqual(config["hooks"]["state"], {"existing": {"trusted_hash": "original"}})
            self.assertNotIn("screen_reader_detection_done", config.get("tui", {}))
            self.assertNotIn("model_availability_nux", config.get("tui", {}))

    def test_codex_sync_rejects_invalid_toml_without_changing_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live, repo = root / "live.toml", root / "repo.toml"
            live.write_text('model = [\n')
            repo.write_text('model = "old"\n')
            result = subprocess.run(
                ["uv", "run", "--no-project", "--script",
                 str(REPO_ROOT / "mac/scripts/ai/sync_codex_config.py"), str(live), str(repo),
                 str(REPO_ROOT / "shell/zsh/alias/utils.zsh")],
                env=sanitized_env({"HOME": directory}), capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(repo.read_text(), 'model = "old"\n')

    def test_removed_context_mode_and_i_have_adhd_stay_unregistered(self):
        for path in ("ai/claude/settings.json", "ai/gemini/settings.json"):
            settings_text = read_text(path)
            with self.subTest(path=path):
                json.loads(settings_text)
                self.assertNotIn("context-mode", settings_text)
                self.assertNotIn("i-have-adhd", settings_text)

        for path in ("mac/scripts/ai/claude.sh", "mac/scripts/ai/codex.sh", "mac/scripts/ai/gemini.sh", "mac/scripts/common.sh"):
            with self.subTest(path=path):
                self.assertNotIn("context-mode", read_text(path))
                self.assertNotIn("i-have-adhd", read_text(path))

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_codex_config_enables_plugin_hooks(self):
        config = tomllib.loads(read_text("ai/codex/config.toml"))

        self.assertTrue(config["features"]["hooks"])
        self.assertTrue(config["features"]["plugin_hooks"])

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

    def test_claude_settings_register_ponytail_plugin(self):
        settings = json.loads(read_text("ai/claude/settings.json"))

        self.assertTrue(settings["enabledPlugins"]["ponytail@ponytail"])
        self.assertEqual(
            settings["extraKnownMarketplaces"]["ponytail"],
            {
                "source": {
                    "repo": "DietrichGebert/ponytail",
                    "source": "github",
                }
            },
        )

    def test_claude_ponytail_setup_uses_upstream_marketplace(self):
        script = read_text("mac/scripts/ai/claude.sh")

        self.assertIn("function setup_claude_ponytail()", script)
        self.assertIn("claude plugin marketplace add DietrichGebert/ponytail", script)
        self.assertIn("claude plugin marketplace update ponytail", script)
        self.assertIn("ponytail@ponytail", script)

        # marketplace名(ponytail)がrepo owner(DietrichGebert)と混同され、
        # repo slugをplugin ID/参照に誤用していないことを確認する
        self.assertNotIn("ponytail@DietrichGebert/ponytail", script)

    def test_claude_settings_register_cache_tools_plugin(self):
        settings = json.loads(read_text("ai/claude/settings.json"))

        self.assertTrue(settings["enabledPlugins"]["cache-tools@claude-code-cache-tools"])
        self.assertEqual(
            settings["extraKnownMarketplaces"]["claude-code-cache-tools"],
            {
                "source": {
                    "repo": "Sigsiguma/claude-code-cache-tools",
                    "source": "github",
                }
            },
        )

    def test_claude_cache_tools_setup_uses_upstream_marketplace(self):
        script = read_text("mac/scripts/ai/claude.sh")

        self.assertIn("function setup_claude_cache_tools()", script)
        self.assertIn("claude plugin marketplace add Sigsiguma/claude-code-cache-tools", script)
        self.assertIn("claude plugin marketplace update claude-code-cache-tools", script)
        self.assertIn("cache-tools@claude-code-cache-tools", script)

        # marketplace名(claude-code-cache-tools)とrepo slug(Sigsiguma/...)を取り違え、
        # plugin ID/updateにrepo slugを誤用していないことを確認する
        self.assertNotIn("cache-tools@Sigsiguma/claude-code-cache-tools", script)
        self.assertNotIn("marketplace update Sigsiguma", script)

    def test_codex_ponytail_setup_uses_installed_guard_not_config_toml_fallback(self):
        codex = read_text("mac/scripts/ai/codex.sh")

        self.assertIn("function setup_codex_ponytail()", codex)
        self.assertIn("codex plugin marketplace add DietrichGebert/ponytail", codex)
        self.assertIn("codex plugin marketplace upgrade ponytail", codex)
        self.assertIn("codex plugin add ponytail@ponytail", codex)
        self.assertNotIn("ponytail@DietrichGebert/ponytail", codex)

        # ponytail は git 解決される marketplace のため .installed[] に現れる
        # (bundled snapshot の openai-curated とは異なる)。config.toml への
        # フォールバック grep は不要であり、誤って追加されていないことを確認する。
        self.assertNotIn(
            "/usr/bin/grep -Fq \"[plugins.'ponytail@ponytail']\"", codex
        )

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

    def test_superpowers_setup_uses_noninteractive_flags(self):
        claude = read_text("mac/scripts/ai/claude.sh")
        gemini = read_text("mac/scripts/ai/gemini.sh")

        # mac/initialize と mac/update を対話なしで完走させるため、
        # superpowers のインストール/更新は確認プロンプトを抑止する必要がある。
        self.assertIn(
            "claude plugin install -y superpowers@claude-plugins-official", claude
        )
        self.assertIn(
            "claude plugin update -y superpowers@claude-plugins-official", claude
        )

        gemini_install = (
            "gemini extensions install https://github.com/obra/superpowers"
            " --auto-update --consent --skip-settings"
        )
        self.assertIn(gemini_install, gemini)

        # codex plugin add には確認スキップ用フラグが存在しないため、-y 相当は付けられない。
        # 誤って追加されると codex が未知フラグで落ちるので、その回帰を明示的に禁止する。
        codex = read_text("mac/scripts/ai/codex.sh")
        self.assertNotIn("codex plugin add -y", codex)
        self.assertIn("codex plugin add superpowers@openai-curated", codex)

    def test_codex_superpowers_guard_falls_back_to_config_toml(self):
        codex = read_text("mac/scripts/ai/codex.sh")

        # codex plugin list --json はローカル marketplace(openai-curated) の項目を
        # 返さないため、.installed だけを見る guard は add 成功後も一致せず
        # plugin add が毎回走る（= 毎回インストール対話が発生しうる）。
        # config.toml の plugin テーブルを併用することでのみ再実行を防げる。
        self.assertIn(
            "/usr/bin/grep -Fq \"[plugins.'superpowers@openai-curated']\" \"$HOME/.codex/config.toml\"",
            codex,
        )

        # guard は OR 条件でなければならない。.installed 単独に戻すと上記の回帰が起きる。
        superpowers_body = codex.split("function setup_codex_superpowers()", 1)[1]
        superpowers_body = superpowers_body.split("\n}", 1)[0]
        self.assertIn("||", superpowers_body)


if __name__ == "__main__":
    unittest.main()
