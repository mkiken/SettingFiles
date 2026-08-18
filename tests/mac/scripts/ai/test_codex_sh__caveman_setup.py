import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT


CODEX_SCRIPT = REPO_ROOT / "mac/scripts/ai/codex.sh"


class CodexCavemanSetupTest(unittest.TestCase):
    def run_setup(
        self,
        function_name: str,
        *,
        installed: bool = False,
        npx_result: int = 0,
        create_skill: bool = True,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            home_dir = temp_path / "home"
            skill_path = home_dir / ".agents/skills/caveman/SKILL.md"
            call_log = temp_path / "calls.log"

            if installed:
                skill_path.parent.mkdir(parents=True)
                skill_path.write_text("installed\n", encoding="utf-8")

            script = f'''
Repo="{REPO_ROOT}/"
HOME="{home_dir}"
source "{CODEX_SCRIPT}"

function npx() {{
  print -r -- "npx $*" >> "{call_log}"
  if [[ {str(create_skill).lower()} == true && "$3" == "add" ]]; then
    mkdir -p "$HOME/.agents/skills/caveman"
    print -r -- installed > "$HOME/.agents/skills/caveman/SKILL.md"
  fi
  return {npx_result}
}}

{function_name}
'''
            result = subprocess.run(
                ["zsh", "-c", script, "codex-caveman-test"],
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

    def test_setup_installs_caveman_globally_when_missing(self):
        result, calls = self.run_setup("setup_codex_caveman")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            [
                "npx --yes skills@latest add JuliusBrussee/caveman --agent codex "
                "--global --skill caveman --yes"
            ],
        )

    def test_setup_skips_existing_caveman_skill(self):
        result, calls = self.run_setup("setup_codex_caveman", installed=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_update_updates_existing_caveman_skill(self):
        result, calls = self.run_setup("update_codex_caveman", installed=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            ["npx --yes skills@latest update caveman --global --yes"],
        )

    def test_update_installs_missing_caveman_skill(self):
        result, calls = self.run_setup("update_codex_caveman")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            [
                "npx --yes skills@latest add JuliusBrussee/caveman --agent codex "
                "--global --skill caveman --yes"
            ],
        )

    def test_setup_fails_when_install_command_fails(self):
        result, _ = self.run_setup("setup_codex_caveman", npx_result=1)

        self.assertNotEqual(result.returncode, 0)

    def test_setup_fails_when_skill_is_not_created(self):
        result, _ = self.run_setup("setup_codex_caveman", create_skill=False)

        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
