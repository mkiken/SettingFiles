import json
import shlex
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env


class CodexReviewAliasTest(unittest.TestCase):
    def run_command(self, command, exit_code=0):
        script = f'''
source {shlex.quote(str(REPO_ROOT / "shell/zsh/alias/ai/codex.zsh"))}
cx() {{
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@"
    return {exit_code}
}}
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

    def test_review_post_selects_terra_high_and_passes_skill_arguments(self):
        for arguments, suffix in (
            ("", ""),
            ("'run with spaces' '1,3'", "run with spaces 1,3"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_command(f"cx-review-post {arguments}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout),
                    [
                        "--model", "gpt-5.6-terra",
                        "-c", 'model_reasoning_effort="high"',
                        "--dangerously-bypass-approvals-and-sandbox",
                        f"$review-post {suffix}",
                    ],
                )

    def test_review_post_preserves_codex_exit_code(self):
        result = self.run_command("cx-review-post", exit_code=7)
        self.assertEqual(result.returncode, 7)

    def test_review_fix_selects_sol_and_passes_skill_arguments(self):
        for arguments, suffix in (
            ("", ""),
            ("'run with spaces' '1,3'", "run with spaces 1,3"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_command(f"cx-review-fix {arguments}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout),
                    ["--model", "gpt-6.1-sol", f"$review-fix {suffix}"],
                )

    def test_review_fix_preserves_codex_exit_code(self):
        result = self.run_command("cx-review-fix", exit_code=7)
        self.assertEqual(result.returncode, 7)
