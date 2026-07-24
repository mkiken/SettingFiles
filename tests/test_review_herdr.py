import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"


def run_review_herdr(
    args: str,
    *,
    git_name: str = "repo",
    git_name_defined: bool = True,
    workspace_list_json: str = '{"result":{"workspaces":[]}}',
    workspace_create_exit: int = 0,
    workspace_create_json: str = '{"result":{"workspace":{"workspace_id":"w9"}}}',
    tab_create_exit: int = 0,
    tab_create_json: str = '{"result":{"root_pane":{"pane_id":"w9:p2"}}}',
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """stub herdr/jq/_review_window_git_name/cl-*/gm-*/cx-* 付きでai.zshのHerdr review系関数を
    実行し、(結果, herdr呼び出しログ) を返す。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "calls.log"
        review_git_name_fn = (
            f'_review_window_git_name() {{ printf "%s" "{git_name}"; }}'
            if git_name_defined
            else ""
        )
        script = f'''
LOG="{log_path}"
{review_git_name_fn}
cl-pr-review() {{ printf '%s\\n' "cl-pr-review-called: $*" >> "$LOG"; }}
cl-pr-review-subagents() {{ printf '%s\\n' "cl-pr-review-subagents-called: $*" >> "$LOG"; }}
gm-pr-review() {{ printf '%s\\n' "gm-pr-review-called: $*" >> "$LOG"; }}
gm-pr-review-subagents() {{ printf '%s\\n' "gm-pr-review-subagents-called: $*" >> "$LOG"; }}
cx-pr-review() {{ printf '%s\\n' "cx-pr-review-called: $*" >> "$LOG"; }}
cx-pr-review-subagent() {{ printf '%s\\n' "cx-pr-review-subagent-called: $*" >> "$LOG"; }}
herdr() {{
    printf '%s\\n' "herdr $*" >> "$LOG"
    case "$1" in
        workspace)
            if [[ "$2" == "list" ]]; then
                printf '%s' '{workspace_list_json}'
                return 0
            elif [[ "$2" == "create" ]]; then
                if [[ {workspace_create_exit} -eq 0 ]]; then
                    printf '%s' '{workspace_create_json}'
                fi
                return {workspace_create_exit}
            elif [[ "$2" == "focus" ]]; then
                return 0
            fi
            ;;
        tab)
            if [[ "$2" == "create" ]]; then
                if [[ {tab_create_exit} -eq 0 ]]; then
                    printf '%s' '{tab_create_json}'
                fi
                return {tab_create_exit}
            fi
            ;;
        pane)
            if [[ "$2" == "run" ]]; then
                return 0
            fi
            ;;
        wait)
            [[ "$2" == "output" ]] && return 0
            ;;
    esac
}}
jq() {{
    python3 -c 'import json,sys
d=json.load(sys.stdin)
res=d.get("result",{{}})
if "workspaces" in res:
    for w in res["workspaces"]:
        if w.get("label")=="review":
            print(w.get("workspace_id"))
elif "workspace" in res:
    print(res.get("workspace",{{}}).get("workspace_id") or "null")
elif "root_pane" in res:
    print(res.get("root_pane",{{}}).get("pane_id") or "null")
' "$@"
}}
source "{AI_ALIASES}"
{args}
'''
        result = subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env={"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
            text=True,
            capture_output=True,
            check=False,
        )
        calls = log_path.read_text().splitlines() if log_path.exists() else []
        return result, calls


def real_pane_run_commands(calls: list[str]) -> list[str]:
    """呼び出しログから、_herdr_wait_shell_readyのマーカー送信を除いた
    「本命コマンド」の pane run 呼び出しだけを抜き出す。"""
    return [
        c for c in calls
        if c.startswith("herdr pane run") and "print -r --" not in c
    ]


class HerdrResolveReviewWorkspaceTest(unittest.TestCase):
    def test_existing_review_workspace_is_reused_without_create(self):
        result, calls = run_review_herdr(
            '_herdr_resolve_review_workspace "/tmp/work"',
            workspace_list_json='{"result":{"workspaces":['
            '{"label":"other","workspace_id":"w1"},'
            '{"label":"review","workspace_id":"w6"}'
            ']}}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "w6")
        self.assertFalse(any(c.startswith("herdr workspace create") for c in calls), calls)

    def test_no_existing_review_workspace_creates_one(self):
        result, calls = run_review_herdr(
            '_herdr_resolve_review_workspace "/tmp/work"',
            workspace_list_json='{"result":{"workspaces":[]}}',
            workspace_create_json='{"result":{"workspace":{"workspace_id":"w9"}}}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "w9")
        create_calls = [c for c in calls if c.startswith("herdr workspace create")]
        self.assertEqual(len(create_calls), 1, calls)
        self.assertIn("--label review", create_calls[0])
        self.assertIn("--cwd /tmp/work", create_calls[0])

    def test_multiple_review_workspaces_returns_first(self):
        result, _ = run_review_herdr(
            '_herdr_resolve_review_workspace "/tmp/work"',
            workspace_list_json='{"result":{"workspaces":['
            '{"label":"review","workspace_id":"w6"},'
            '{"label":"review","workspace_id":"w7"}'
            ']}}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "w6")

    def test_workspace_create_failure_returns_error(self):
        result, _ = run_review_herdr(
            '_herdr_resolve_review_workspace "/tmp/work"',
            workspace_list_json='{"result":{"workspaces":[]}}',
            workspace_create_exit=1,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("herdr workspace createに失敗しました", result.stderr)

    def test_workspace_create_null_id_returns_error(self):
        result, _ = run_review_herdr(
            '_herdr_resolve_review_workspace "/tmp/work"',
            workspace_list_json='{"result":{"workspaces":[]}}',
            workspace_create_json='{"result":{"workspace":{"workspace_id":null}}}',
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("workspace_id取得に失敗しました", result.stderr)


class ReviewHerdrDispatchTestBase:
    """review系Herdr関数3つ (_review_herdr/_review_subagents_herdr/_review_all_herdr) 共通の
    table-drivenテスト。サブクラスがfunc_name/expected_*を指定する。"""

    func_name: str
    claude_prefix: str
    gemini_prefix: str
    codex_prefix: str

    def test_all_three_ais_get_new_tabs_in_same_review_workspace(self):
        result, calls = run_review_herdr(
            f'{self.func_name} 123',
            workspace_list_json='{"result":{"workspaces":['
            '{"label":"review","workspace_id":"w6"}'
            ']}}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        tab_creates = [c for c in calls if c.startswith("herdr tab create")]
        self.assertEqual(len(tab_creates), 3, calls)
        for c in tab_creates:
            self.assertIn("--workspace w6", c)
        self.assertFalse(any(c.startswith("herdr workspace create") for c in calls), calls)

    def test_no_existing_review_workspace_creates_and_reuses_across_tabs(self):
        result, calls = run_review_herdr(f'{self.func_name} 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        create_calls = [c for c in calls if c.startswith("herdr workspace create")]
        self.assertEqual(len(create_calls), 1, calls)
        tab_creates = [c for c in calls if c.startswith("herdr tab create")]
        self.assertEqual(len(tab_creates), 3, calls)
        for c in tab_creates:
            self.assertIn("--workspace w9", c)

    def test_tab_labels_carry_ai_specific_emoji_and_review_glyph(self):
        result, calls = run_review_herdr(f'{self.func_name} 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        tab_creates = [c for c in calls if c.startswith("herdr tab create")]
        self.assertTrue(any(f"--label {self.claude_prefix}🔍repo" in c for c in tab_creates), tab_creates)
        self.assertTrue(any(f"--label {self.gemini_prefix}🔍repo" in c for c in tab_creates), tab_creates)
        self.assertTrue(any(f"--label {self.codex_prefix}🔍repo" in c for c in tab_creates), tab_creates)

    def test_claude_runs_via_new_tab_not_current_pane(self):
        result, calls = run_review_herdr(f'{self.func_name} 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        # 旧実装は現在paneで直接cl-pr-review*を呼んでいたが、新実装はpane run経由のみ
        self.assertFalse(any("-called:" in c for c in calls), calls)

    def test_workspace_focused_after_all_tabs_created(self):
        result, calls = run_review_herdr(f'{self.func_name} 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("herdr workspace focus w9", calls)
        focus_idx = calls.index("herdr workspace focus w9")
        tab_create_idxs = [i for i, c in enumerate(calls) if c.startswith("herdr tab create")]
        self.assertEqual(len(tab_create_idxs), 3)
        self.assertGreater(focus_idx, max(tab_create_idxs))

    def test_claude_tab_creation_failure_skips_remaining_tabs(self):
        result, calls = run_review_herdr(
            f'{self.func_name} 123',
            tab_create_exit=1,
        )
        self.assertEqual(result.returncode, 1)
        tab_creates = [c for c in calls if c.startswith("herdr tab create")]
        self.assertEqual(len(tab_creates), 1, calls)
        self.assertFalse(any(c.startswith("herdr workspace focus") for c in calls), calls)

    def test_git_name_lookup_failure_returns_error_before_any_herdr_call(self):
        result, calls = run_review_herdr(
            f'{self.func_name} 123',
            git_name_defined=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("_review_window_git_name が見つかりません", result.stderr)
        self.assertEqual(calls, [])


class ReviewHerdrTest(ReviewHerdrDispatchTestBase, unittest.TestCase):
    func_name = "_review_herdr"
    claude_prefix = "✴️"
    gemini_prefix = "💎"
    codex_prefix = "🪷"

    def test_command_builders_use_non_subagent_review_functions(self):
        result, calls = run_review_herdr('_review_herdr 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        joined = " ".join(real_pane_run_commands(calls))
        self.assertIn("cl-pr-review 123", joined)
        self.assertIn("gm-pr-review 123", joined)
        self.assertIn("cx-pr-review 123", joined)
        self.assertNotIn("cl-pr-review-subagents", joined)


class ReviewSubagentsHerdrTest(ReviewHerdrDispatchTestBase, unittest.TestCase):
    func_name = "_review_subagents_herdr"
    claude_prefix = "✴️"
    gemini_prefix = "💎"
    codex_prefix = "🪷"

    def test_command_builders_use_subagent_review_functions(self):
        result, calls = run_review_herdr('_review_subagents_herdr 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        joined = " ".join(real_pane_run_commands(calls))
        self.assertIn("cl-pr-review-subagents 123", joined)
        self.assertIn("gm-pr-review-subagents 123", joined)
        self.assertIn("cx-pr-review-subagent 123", joined)


class ReviewAllHerdrTest(ReviewHerdrDispatchTestBase, unittest.TestCase):
    func_name = "_review_all_herdr"
    claude_prefix = "✴️"
    gemini_prefix = "💎"
    codex_prefix = "🪷"

    def test_claude_uses_subagents_variant_like_gemini_and_codex(self):
        result, calls = run_review_herdr('_review_all_herdr 123')
        self.assertEqual(result.returncode, 0, result.stderr)
        joined = " ".join(real_pane_run_commands(calls))
        self.assertIn("cl-pr-review-subagents 123", joined)


if __name__ == "__main__":
    unittest.main()
