import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_SCRIPT = REPO_ROOT / "mac/scripts/ai/codex.sh"


class CodexClaudeMemSetupTest(unittest.TestCase):
    def run_setup_codex_claude_mem(
        self,
        *,
        plugin_list_json: str,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            call_log = Path(temp_dir) / "calls.log"

            script = f'''
Repo="{REPO_ROOT}/"
source "{CODEX_SCRIPT}"

function require_ai_setup_command() {{
  return 0
}}

function codex() {{
  if [[ "$1" == "plugin" && "$2" == "list" ]]; then
    printf '%s\\n' {plugin_list_json!r}
  fi
}}

function setup_claude_mem_for_ide() {{
  printf 'setup_claude_mem_for_ide %s\\n' "$1" >> "{call_log}"
  return 0
}}

function setup_claude_mem_runtime() {{
  printf 'setup_claude_mem_runtime\\n' >> "{call_log}"
  return 0
}}

setup_codex_claude_mem
'''
            result = subprocess.run(
                ["zsh", "-c", script, "codex-claude-mem-test"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            calls = (
                call_log.read_text(encoding="utf-8").splitlines()
                if call_log.exists()
                else []
            )
            return result, calls

    def test_skips_install_when_claude_mem_already_installed(self):
        installed_json = (
            '{"installed":[{"pluginId":"claude-mem@claude-mem-local",'
            '"name":"claude-mem","marketplaceName":"claude-mem-local",'
            '"installed":true}]}'
        )

        result, calls = self.run_setup_codex_claude_mem(
            plugin_list_json=installed_json
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already installed", result.stdout)
        self.assertNotIn("setup_claude_mem_for_ide codex-cli", calls)
        self.assertIn("setup_claude_mem_runtime", calls)

    def test_installs_when_claude_mem_not_installed(self):
        empty_json = '{"installed":[]}'

        result, calls = self.run_setup_codex_claude_mem(plugin_list_json=empty_json)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("setup_claude_mem_for_ide codex-cli", calls)
        self.assertIn("setup_claude_mem_runtime", calls)

    def test_runtime_setup_always_runs_regardless_of_install_state(self):
        for label, plugin_list_json in (
            ("installed", '{"installed":[{"name":"claude-mem","installed":true}]}'),
            ("not-installed", '{"installed":[]}'),
        ):
            with self.subTest(state=label):
                result, calls = self.run_setup_codex_claude_mem(
                    plugin_list_json=plugin_list_json
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("setup_claude_mem_runtime", calls)


if __name__ == "__main__":
    unittest.main()
