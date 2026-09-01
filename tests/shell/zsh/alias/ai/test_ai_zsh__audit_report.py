import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

AI_ZSH = REPO_ROOT / "shell" / "zsh" / "alias" / "ai" / "ai.zsh"


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-c", f'SET="{REPO_ROOT}"; source "{AI_ZSH}"; {snippet}'],
        capture_output=True, text=True,
    )


class AuditReportFunctionTest(unittest.TestCase):
    def test_audit_report_is_defined(self):
        self.assertEqual(run_zsh("typeset -f -- audit-report >/dev/null").returncode, 0)

    def stub_snippet(self, temp_dir, platform_arg="", make_report=True):
        run_dir = Path(temp_dir) / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        if make_report:
            (run_dir / "report.html").write_text("<h1>report</h1>", encoding="utf-8")
        calls = Path(temp_dir) / "calls.log"
        # run_dir解決とサーバー起動をスタブ化し、引数だけを記録する
        return calls, f'''
bash() {{ printf '%s\\n' "bash $*" >> "{calls}"; printf '%s\\n' "{run_dir}"; }}
nohup() {{ printf '%s\\n' "nohup $*" >> "{calls}"; }}
audit-report {platform_arg}
'''

    def test_defaults_to_claude_platform(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            calls, snippet = self.stub_snippet(temp_dir)
            result = run_zsh(snippet)
            self.assertEqual(result.returncode, 0, result.stderr)
            logged = calls.read_text(encoding="utf-8")
            self.assertIn("ai_audit_run_dir.sh --latest claude", logged)

    def test_accepts_an_explicit_platform(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            calls, snippet = self.stub_snippet(temp_dir, platform_arg="codex")
            result = run_zsh(snippet)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ai_audit_run_dir.sh --latest codex", calls.read_text(encoding="utf-8"))

    def test_serves_with_open_flag(self):
        # エージェントと違い検証する主体がいないため、シェル関数側は --open を渡す
        with tempfile.TemporaryDirectory() as temp_dir:
            calls, snippet = self.stub_snippet(temp_dir)
            run_zsh(snippet)
            logged = calls.read_text(encoding="utf-8")
            self.assertIn("serve_review_report.py", logged)
            self.assertIn("--open", logged)

    def test_errors_when_report_html_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            calls, snippet = self.stub_snippet(temp_dir, make_report=False)
            result = run_zsh(snippet)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("report.htmlが見つかりません", result.stderr)
            self.assertNotIn("nohup", calls.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
