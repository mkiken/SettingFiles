import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
CODEX_SCRIPT = REPO_ROOT / "mac/scripts/ai/codex.sh"


class CodexPonytailSetupTest(unittest.TestCase):
    def run_setup_codex_ponytail(
        self,
        *,
        marketplace_list: str = "ponytail",
        plugin_list_json: str = '{"installed":[]}',
        plugin_add_exit_code: int = 0,
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
  if [[ "$1" == "plugin" && "$2" == "marketplace" && "$3" == "list" ]]; then
    printf '%s\\n' {marketplace_list!r}
  elif [[ "$1" == "plugin" && "$2" == "marketplace" && "$3" == "add" ]]; then
    printf 'plugin marketplace add %s\\n' "$4" >> "{call_log}"
  elif [[ "$1" == "plugin" && "$2" == "marketplace" && "$3" == "upgrade" ]]; then
    printf 'plugin marketplace upgrade %s\\n' "$4" >> "{call_log}"
  elif [[ "$1" == "plugin" && "$2" == "list" ]]; then
    printf '%s\\n' {plugin_list_json!r}
  elif [[ "$1" == "plugin" && "$2" == "add" ]]; then
    printf 'plugin add %s\\n' "$3" >> "{call_log}"
    return {plugin_add_exit_code}
  fi
}}

setup_codex_ponytail
'''
            result = subprocess.run(
                ["zsh", "-c", script, "codex-ponytail-test"],
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

    def test_skips_install_when_ponytail_already_installed(self):
        installed_json = (
            '{"installed":[{"pluginId":"ponytail@ponytail",'
            '"name":"ponytail","marketplaceName":"ponytail",'
            '"installed":true}]}'
        )

        result, calls = self.run_setup_codex_ponytail(plugin_list_json=installed_json)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already installed", result.stdout)
        self.assertFalse(
            any(call.startswith("plugin add ") for call in calls),
            calls,
        )

    def test_installs_when_ponytail_not_installed(self):
        result, calls = self.run_setup_codex_ponytail(
            plugin_list_json='{"installed":[]}'
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin add ponytail@ponytail", calls)

    def test_skips_marketplace_add_when_already_registered(self):
        result, calls = self.run_setup_codex_ponytail(
            marketplace_list="context-mode\nponytail\nsuperpowers",
            plugin_list_json='{"installed":[]}',
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            any(call.startswith("plugin marketplace add ") for call in calls),
            calls,
        )

    def test_adds_marketplace_when_not_registered(self):
        result, calls = self.run_setup_codex_ponytail(
            marketplace_list="context-mode\nsuperpowers",
            plugin_list_json='{"installed":[]}',
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin marketplace add DietrichGebert/ponytail", calls)

    def test_propagates_failure_from_plugin_add(self):
        result, _calls = self.run_setup_codex_ponytail(
            plugin_list_json='{"installed":[]}',
            plugin_add_exit_code=1,
        )

        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
