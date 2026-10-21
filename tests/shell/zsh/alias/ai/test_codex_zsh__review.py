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

    def test_review_post_selects_sol_and_passes_skill_arguments(self):
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
                        "--model", "gpt-6.1-sol",
                        "--dangerously-bypass-approvals-and-sandbox",
                        f"$review-post {suffix}",
                    ],
                )

    def test_review_post_preserves_codex_exit_code(self):
        result = self.run_command("cx-review-post", exit_code=7)
        self.assertEqual(result.returncode, 7)

    def test_migrated_workflows_use_cxs_without_reasoning_override(self):
        cases = (
            (
                "cx-pr-body 'two words'",
                ["--dangerously-bypass-approvals-and-sandbox"],
                "$pr-body PR #123 のbodyを生成して two words",
            ),
            (
                "cx-review-post 'run with spaces' '1,3'",
                ["--dangerously-bypass-approvals-and-sandbox"],
                "$review-post run with spaces 1,3",
            ),
            (
                "_cx-pr-comment-implement 'https://github.com/acme/widget/pull/42#discussion_r123' 'two words'",
                [],
                "$pr-comment-implement https://github.com/acme/widget/pull/42#discussion_r123 two words",
            ),
        )
        for command, flags, prompt in cases:
            for model in ("gpt-6.1-sol", "test-sol"):
                for exit_code in (0, 7):
                    with self.subTest(command=command, model=model, exit_code=exit_code):
                        setup = 'gh() { print -r -- 123; }\n'
                        # Trap Terra calls; replacing cxs proves callers share its model selection.
                        setup += 'cxt() { return 98; }\ncxteh() { return 99; }\n'
                        if model == "test-sol":
                            setup += 'cxs() { cx --model test-sol "$@"; }\n'
                        result = self.run_command(setup + command, exit_code=exit_code)
                        self.assertEqual(result.returncode, exit_code, result.stderr)
                        self.assertEqual(
                            json.loads(result.stdout),
                            ["--model", model, *flags, prompt],
                        )

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
