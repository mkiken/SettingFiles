import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

AI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"

GEMINI_LISTING = """Available sessions for this project (2):
  1. Old [bracket] title (1 day ago) [aaaa-old]
  2. Recent session (1 hour ago) [bbbb-new]
"""


class AisResumeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name).resolve()
        # PATH 外に置いた罠。スタブ(cl/cx/gm)を迂回して本物の CLI を呼んだら痕跡が残る
        self.trap_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.trap_dir, ignore_errors=True))
        self.trace = self.trap_dir / "trace"
        for name in ("claude", "codex", "gemini"):
            exe = self.trap_dir / name
            exe.write_text(f"#!/bin/sh\necho {name} >> {shlex.quote(str(self.trace))}\n")
            exe.chmod(0o755)

    def run_zsh(self, body, *, fzf_output=None):
        fzf_stub = "fzf() { return 130 }"
        if fzf_output is not None:
            fzf_stub = f"fzf() {{ cat >/dev/null; printf '%s\\n' {shlex.quote(fzf_output)} }}"
        script = f"""
cl() {{ print -r -- "cl pwd=$PWD args=$*" }}
cx() {{ print -r -- "cx pwd=$PWD args=$*" }}
gm() {{
    if [[ "$*" == *--list-sessions* ]]; then
        print -r -- {shlex.quote(GEMINI_LISTING)}
    else
        print -r -- "gm pwd=$PWD args=$*"
    fi
}}
python3() {{ print -r -- "" }}
{fzf_stub}
source {shlex.quote(str(AI_ZSH))}
{body}
"""
        return subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env=sanitized_env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_trap_untouched(self):
        self.assertFalse(self.trace.exists())

    def test_claude_resumes_in_project_directory(self):
        result = self.run_zsh(f"_ais_resume claude sid-1 {shlex.quote(str(self.project))}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"cl pwd={self.project} args=--resume sid-1")

    def test_codex_resumes_in_project_directory(self):
        result = self.run_zsh(f"_ais_resume codex sid-2 {shlex.quote(str(self.project))}")
        self.assertEqual(result.stdout.strip(), f"cx pwd={self.project} args=resume sid-2")

    def test_gemini_resolves_uuid_to_index_even_when_title_contains_brackets(self):
        old = self.run_zsh(f"_ais_resume gemini aaaa-old {shlex.quote(str(self.project))}")
        new = self.run_zsh(f"_ais_resume gemini bbbb-new {shlex.quote(str(self.project))}")
        self.assertEqual(old.stdout.strip(), f"gm pwd={self.project} args=--resume 1")
        self.assertEqual(new.stdout.strip(), f"gm pwd={self.project} args=--resume 2")

    def test_gemini_unknown_uuid_fails_without_launching(self):
        result = self.run_zsh(f"_ais_resume gemini nope {shlex.quote(str(self.project))}")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("args=--resume", result.stdout)
        self.assertIn("resume できません", result.stderr)

    def test_missing_or_empty_cwd_fails_without_launching(self):
        for cwd in ("/nonexistent/dir/for/ais", ""):
            with self.subTest(cwd=cwd):
                result = self.run_zsh(f"_ais_resume claude sid {shlex.quote(cwd)}")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("作業ディレクトリが見つかりません", result.stderr)

    def test_unknown_agent_fails(self):
        result = self.run_zsh(f"_ais_resume bogus sid {shlex.quote(str(self.project))}")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_resume_does_not_change_callers_directory(self):
        result = self.run_zsh(f"_ais_resume claude sid {shlex.quote(str(self.project))} >/dev/null; print -r -- \"after=$PWD\"")
        self.assertEqual(result.stdout.strip(), f"after={REPO_ROOT}")

    def test_ais_cancelled_fzf_launches_nothing_and_succeeds(self):
        result = self.run_zsh("ais; print -r -- \"rc=$?\"")
        self.assertEqual(result.stdout.strip(), "rc=0")

    def test_ais_resumes_selected_row_with_empty_middle_field_preserved(self):
        row = "\t".join(["claude", "sid-9", str(self.project), "/some/file", "display text"])
        result = self.run_zsh("ais", fzf_output=row)
        self.assertEqual(result.stdout.strip(), f"cl pwd={self.project} args=--resume sid-9")

    def test_ais_with_empty_cwd_field_does_not_shift_columns(self):
        row = "\t".join(["gemini", "bbbb-new", "", "/some/file", "display text"])
        result = self.run_zsh("ais", fzf_output=row)
        self.assertEqual(result.returncode, 1)
        self.assertIn("作業ディレクトリが見つかりません", result.stderr)
        self.assertNotIn("未知のエージェント", result.stderr)

    def test_stubs_never_bypassed_to_real_cli(self):
        self.run_zsh(f"_ais_resume claude s {shlex.quote(str(self.project))}; _ais_resume codex s {shlex.quote(str(self.project))}")
        self.assert_trap_untouched()


if __name__ == "__main__":
    unittest.main()
