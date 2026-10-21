import json
import shlex
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env

GEMINI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/gemini.zsh"


class GeminiResumeAliasTest(unittest.TestCase):
    def run_command(self, command: str) -> subprocess.CompletedProcess:
        script = f'''
no_notify() {{
    "$@"
}}
homebrew_run() {{
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@"
}}
source {shlex.quote(str(GEMINI_ZSH))}
{command}
'''
        return subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env=sanitized_env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_gmr_passes_resume_flag_without_arguments(self):
        result = self.run_command("gmr")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--resume"],
        )

    def test_gmr_passes_resume_flag_with_arguments(self):
        result = self.run_command("gmr latest 'explain this'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--resume", "latest", "explain this"],
        )

    def test_gmpr_passes_model_pro_and_resume_flag(self):
        result = self.run_command("gmpr")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--model", "pro", "--resume"],
        )


if __name__ == "__main__":
    unittest.main()
