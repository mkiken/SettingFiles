import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_ZSH = REPO_ROOT / "shell" / "zsh" / "alias" / "ai" / "ai.zsh"


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-c", f'SET="{REPO_ROOT}"; source "{AI_ZSH}"; {snippet}'],
        capture_output=True, text=True,
    )


class AiReviewLauncherTest(unittest.TestCase):
    def test_env_command_prefixes_output_file(self):
        result = run_zsh(
            "_ai_review_env_command /tmp/run/claude.md cl-pr-review 123 'extra note'"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # zshの ${(q)} はスペースをバックスラッシュでクォートする
        self.assertEqual(
            result.stdout.strip(),
            "AI_REVIEW_OUTPUT_FILE=/tmp/run/claude.md cl-pr-review 123 extra\\ note",
        )

    def test_env_tmux_command_appends_shell(self):
        result = run_zsh("_ai_review_env_tmux_command /tmp/run/codex.md cx-pr-review 9")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith("; zsh"))

    def test_review_all_removed(self):
        for name in ("review-all", "_review_all_tmux", "_review_all_herdr"):
            with self.subTest(name=name):
                result = run_zsh(f"typeset -f -- {name} >/dev/null")
                self.assertNotEqual(result.returncode, 0)

    def test_review_functions_exist(self):
        for name in ("review", "review-subagents", "review-merge", "_review_run"):
            with self.subTest(name=name):
                result = run_zsh(f"typeset -f -- {name} >/dev/null")
                self.assertEqual(result.returncode, 0, result.stderr)


class ReviewLaunchHerdrTest(unittest.TestCase):
    """_review_launch_herdr のtab_id受け渡しとメインタブ改名（herdr/下位関数はstub）。"""

    def run_launch(self, pre=""):
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "calls.log"
            snippet = f'''
LOG="{log}"
herdr() {{ printf '%s\\n' "$*" >> "$LOG"; }}
_review_window_git_name() {{ echo "my-branch"; }}
_herdr_resolve_review_workspace() {{ echo "ws1"; }}
# 実体は test_herdr_run_in_new_tab.py で検証済みなので、ここでは連番tab_idを代入するstubにする
_herdr_run_in_new_tab() {{
    printf 'newtab %s\\n' "$*" >> "$LOG"
    local n=$(grep -c "^newtab " "$LOG")
    [[ -n "${{5:-}}" ]] && _ai_pr_review_assign "$5" "t${{n}}"
}}
{pre}
a="" ; b="" ; c=""
_review_launch_herdr a b c /tmp/run cl-fn gm-fn cx-fn 123
print -r -- "rc=$? a=${{a}} b=${{b}} c=${{c}}"
'''
            result = run_zsh(snippet)
            calls = log.read_text().splitlines() if log.exists() else []
        return result, calls

    def test_assigns_three_distinct_tab_ids_and_renames_main_tab(self):
        result, calls = self.run_launch(pre='HERDR_TAB_ID="w1:t0"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rc=0 a=t1 b=t2 c=t3", result.stdout)
        renames = [c for c in calls if c.startswith("tab rename ")]
        self.assertEqual(renames, ["tab rename w1:t0 🔍orchestrator:my-branch"])

    def test_skips_main_tab_rename_when_tab_id_unresolvable(self):
        result, calls = self.run_launch(
            pre='unset HERDR_TAB_ID HERDR_PANE_ID'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rc=0", result.stdout)
        self.assertFalse(any(c.startswith("tab rename ") for c in calls), calls)


class ReviewHandleWaitStatusTest(unittest.TestCase):
    """_review_handle_wait_status のマージ可否分岐（confirmはstub）。"""

    def run_handle(self, status, files=(), confirm_rc=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        run_dir = Path(self.tmp.name)
        for name, content in files:
            (run_dir / name).write_text(content)
        confirm_stub = ""
        if confirm_rc is not None:
            confirm_stub = (
                f'confirm() {{ print -r -- "CONFIRM:$1"; return {confirm_rc}; }}; '
            )
        return run_zsh(
            f'{confirm_stub}_review_handle_wait_status {status} "{run_dir}"; echo "rc=$?"'
        )

    def test_status_zero_merges_without_prompt(self):
        result = self.run_handle(0)
        self.assertIn("rc=0", result.stdout)
        self.assertNotIn("CONFIRM:", result.stdout)

    def test_status_three_without_files_errors_without_prompt(self):
        result = self.run_handle(3, confirm_rc=0)
        self.assertIn("rc=1", result.stdout)
        self.assertNotIn("CONFIRM:", result.stdout)
        self.assertIn("1件もありません", result.stderr)

    def test_status_three_with_partial_files_confirm_yes_merges(self):
        result = self.run_handle(
            3,
            files=(("claude.md", "result"), ("codex.md", "result")),
            confirm_rc=0,
        )
        self.assertIn("rc=0", result.stdout)
        self.assertIn("CONFIRM:", result.stdout)
        self.assertIn("2/3", result.stdout)
        self.assertIn("claude, codex", result.stdout)

    def test_status_three_with_partial_files_confirm_no_defers(self):
        result = self.run_handle(
            3, files=(("claude.md", "result"),), confirm_rc=1,
        )
        self.assertIn("rc=1", result.stdout)
        self.assertIn("review-merge", result.stdout)
        self.assertIn(self.tmp.name, result.stdout)

    def test_status_three_ignores_empty_files_in_count(self):
        # 空ファイルは「揃った」に数えない（境界値）
        result = self.run_handle(
            3,
            files=(("claude.md", ""), ("codex.md", "result")),
            confirm_rc=0,
        )
        self.assertIn("rc=0", result.stdout)
        self.assertIn("1/3", result.stdout)
        self.assertIn("（codex）", result.stdout)

    def test_timeout_status_propagates(self):
        result = self.run_handle(2)
        self.assertIn("rc=2", result.stdout)
        self.assertNotIn("CONFIRM:", result.stdout)


if __name__ == "__main__":
    unittest.main()
