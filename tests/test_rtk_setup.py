import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RTK_SCRIPT = REPO_ROOT / "mac/scripts/ai/rtk.sh"


class RtkSetupTest(unittest.TestCase):
    def run_zsh(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["zsh", "-c", script, "rtk-setup-test"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_hook_reconciliation_preserves_other_hooks_and_migrates_legacy_hook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "third-party-hook",
                                        },
                                        {
                                            "type": "command",
                                            "command": "~/.claude/hooks/rtk-rewrite.sh",
                                        },
                                        {
                                            "type": "command",
                                            "command": "~/.gemini/hooks/rtk-gemini-hook.sh",
                                        },
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_zsh(
                f'''\
source "{RTK_SCRIPT}"
function require_ai_setup_command() {{ return 0; }}
ensure_rtk_hook "{settings_path}" "PreToolUse" "Bash" "rtk hook claude" || exit 1
ensure_rtk_hook "{settings_path}" "PreToolUse" "Bash" "rtk hook claude"
'''
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            groups = settings["hooks"]["PreToolUse"]
            commands = [
                hook["command"] for group in groups for hook in group["hooks"]
            ]
            self.assertEqual(commands.count("rtk hook claude"), 1)
            self.assertIn("third-party-hook", commands)
            self.assertNotIn("~/.claude/hooks/rtk-rewrite.sh", commands)
            self.assertNotIn("~/.gemini/hooks/rtk-gemini-hook.sh", commands)

    def test_invalid_json_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text("{broken", encoding="utf-8")

            result = self.run_zsh(
                f'''\
source "{RTK_SCRIPT}"
function require_ai_setup_command() {{ return 0; }}
ensure_rtk_hook "{settings_path}" "BeforeTool" "run_shell_command" "rtk hook gemini"
'''
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(settings_path.read_text(encoding="utf-8"), "{broken")

    def test_agent_setup_registers_claude_and_gemini_hooks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_zsh(
                f'''\
Repo="{REPO_ROOT}/"
HOME="{temp_dir}"
source "{REPO_ROOT}/mac/scripts/ai/claude.sh"
source "{REPO_ROOT}/mac/scripts/ai/gemini.sh"
source "{REPO_ROOT}/mac/scripts/ai/codex.sh"
function require_ai_setup_command() {{ return 0; }}
function rtk() {{ [[ "$1" == gain ]]; }}
setup_claude_rtk || exit 1
setup_gemini_rtk || exit 1
setup_codex_rtk
'''
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            claude = json.loads(
                (Path(temp_dir) / ".claude/settings.json").read_text(encoding="utf-8")
            )
            gemini = json.loads(
                (Path(temp_dir) / ".gemini/settings.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                "rtk hook claude",
                [
                    hook["command"]
                    for group in claude["hooks"]["PreToolUse"]
                    for hook in group["hooks"]
                ],
            )
            self.assertIn(
                "rtk hook gemini",
                [
                    hook["command"]
                    for group in gemini["hooks"]["BeforeTool"]
                    for hook in group["hooks"]
                ],
            )

    def test_rejects_a_non_rtk_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_zsh(
                f'''\
Repo="{REPO_ROOT}/"
HOME="{temp_dir}"
source "{REPO_ROOT}/mac/scripts/ai/claude.sh"
function require_ai_setup_command() {{ return 0; }}
function rtk() {{ return 1; }}
setup_claude_rtk
'''
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(temp_dir) / ".claude/settings.json").exists())

    def test_brewfile_and_codex_prompt_manage_rtk(self):
        brewfile = (REPO_ROOT / "mac/Brewfile").read_text(encoding="utf-8")
        codex_source = (REPO_ROOT / "ai/codex/codex_base.md").read_text(encoding="utf-8")
        codex_generated = (REPO_ROOT / "ai/codex/_AGENTS.md").read_text(encoding="utf-8")

        self.assertIn('brew "rtk"', brewfile)
        self.assertIn("When `rtk gain` succeeds", codex_source)
        self.assertIn("When `rtk gain` succeeds", codex_generated)


if __name__ == "__main__":
    unittest.main()
