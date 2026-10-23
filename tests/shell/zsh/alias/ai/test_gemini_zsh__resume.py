import json
import shlex
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env

GEMINI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/gemini.zsh"


class GeminiResumeAliasTest(unittest.TestCase):
    def run_command(
        self,
        command: str,
        *,
        cancel_fzf: bool = False,
        missing_fzf: bool = False,
    ) -> subprocess.CompletedProcess:
        env_setup = []
        if cancel_fzf:
            env_setup.append("TEST_FZF_CANCEL=1")

        fzf_mock = '''
fzf() {
    if [[ "${TEST_FZF_CANCEL:-0}" == "1" ]]; then
        return 130
    fi
    if [[ "$*" == *"--tac"* ]]; then
        tail -n 1
    else
        head -n 1
    fi
}
'''
        if missing_fzf:
            fzf_mock = '''
command() {
    if [[ "$1" == "-v" && "$2" == "fzf" ]]; then
        return 1
    fi
    builtin command "$@"
}
'''

        script = f'''
no_notify() {{
    "$@"
}}
homebrew_run() {{
    if [[ "$*" == *"--list-sessions"* ]]; then
        cat <<'EOF'
Available sessions for this project (2):
  1. Old session (1 day ago) [aaa]
  2. Recent session (1 hour ago) [bbb]
EOF
        return 0
    fi
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@"
}}
{fzf_mock}
source {shlex.quote(str(GEMINI_ZSH))}
{" ".join(env_setup)} {command}
'''
        return subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env=sanitized_env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_gmr_selects_session_with_fzf_without_arguments(self):
        result = self.run_command("gmr")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--resume", "2"],
        )

    def test_gmr_passes_resume_flag_with_arguments(self):
        result = self.run_command("gmr latest 'explain this'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--resume", "latest", "explain this"],
        )

    def test_gmpr_selects_session_with_fzf_without_arguments(self):
        result = self.run_command("gmpr")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--model", "pro", "--resume", "2"],
        )

    def test_gmr_does_nothing_when_fzf_cancelled(self):
        result = self.run_command("gmr", cancel_fzf=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_gmr_falls_back_when_fzf_missing(self):
        result = self.run_command("gmr", missing_fzf=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fzf が見つかりません", result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["gemini", "--resume"],
        )


if __name__ == "__main__":
    unittest.main()
