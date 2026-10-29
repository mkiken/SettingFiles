import json
import shlex
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env

GEMINI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/gemini.zsh"


class GeminiApprovalModeTest(unittest.TestCase):
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

    def test_default_approval_mode_is_yolo_for_gm(self):
        result = self.run_command("gm prompt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--approval-mode", "yolo", "prompt"],
        )

    def test_default_approval_mode_is_yolo_for_gmf_and_gmp(self):
        result = self.run_command("gmf task")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--approval-mode", "yolo", "--model", "flash", "task"],
        )

        result = self.run_command("gmp task")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--approval-mode", "yolo", "--model", "pro", "task"],
        )

    def test_gmfp_passes_plan_mode_without_duplicate_approval_mode(self):
        result = self.run_command("gmfp task")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(result.stdout)
        self.assertEqual(args.count("--approval-mode"), 1)
        self.assertEqual(
            args,
            ["gemini", "--model", "flash", "--approval-mode", "plan", "task"],
        )

    def test_gmpp_gmmxp_gmlp_pass_plan_mode_without_duplicates(self):
        for cmd, expected_model in (
            ("gmpp task", "pro"),
            ("gmmxp task", "flash"),
            ("gmlp task", "flash"),
        ):
            with self.subTest(cmd=cmd):
                result = self.run_command(cmd)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads(result.stdout)
                self.assertEqual(args.count("--approval-mode"), 1)
                self.assertEqual(
                    args,
                    ["gemini", "--model", expected_model, "--approval-mode", "plan", "task"],
                )

    def test_explicit_approval_mode_flag_is_respected_without_default_yolo(self):
        result = self.run_command("gm --approval-mode plan task")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(result.stdout)
        self.assertEqual(args.count("--approval-mode"), 1)
        self.assertEqual(
            args,
            ["gemini", "--approval-mode", "plan", "task"],
        )

    def test_explicit_approval_mode_equals_syntax_is_respected(self):
        result = self.run_command("gm --approval-mode=auto_edit task")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--approval-mode=auto_edit", "task"],
        )

    def test_prompt_containing_approval_mode_text_still_gets_default_yolo(self):
        result = self.run_command('gm "explain --approval-mode usage"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--approval-mode", "yolo", "explain --approval-mode usage"],
        )

    def test_approval_mode_after_double_dash_is_positional(self):
        result = self.run_command("gm -- --approval-mode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--approval-mode", "yolo", "--", "--approval-mode"],
        )


if __name__ == "__main__":
    unittest.main()
