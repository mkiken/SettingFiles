import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"


def run_ai_all(
    args: str,
    *,
    env_extra: str = "",
    git_name: str = "repo",
    git_name_defined: bool = True,
    tab_create_exit: int = 0,
    tab_create_json: str = '{"result":{"root_pane":{"pane_id":"w1:p2"}}}',
    tab_rename_exit: int = 0,
    pane_get_tab_id: str = "t1",
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """stub herdr/jq/tmux/_review_window_git_name 付きでai.zshの関数を実行し、
    (結果, herdr/tmux呼び出しログ) を返す。"""
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
herdr() {{
    printf '%s\\n' "herdr $*" >> "$LOG"
    case "$1" in
        tab)
            if [[ "$2" == "create" ]]; then
                if [[ {tab_create_exit} -eq 0 ]]; then
                    printf '%s' '{tab_create_json}'
                fi
                return {tab_create_exit}
            elif [[ "$2" == "rename" ]]; then
                return {tab_rename_exit}
            fi
            ;;
        pane)
            if [[ "$2" == "run" ]]; then
                return 0
            elif [[ "$2" == "get" ]]; then
                printf '%s' '{{"result":{{"pane":{{"tab_id":"{pane_get_tab_id}"}}}}}}'
                return 0
            fi
            ;;
        wait)
            [[ "$2" == "output" ]] && return 0
            ;;
    esac
}}
tmux() {{
    printf '%s\\n' "tmux $*" >> "$LOG"
    return 0
}}
jq() {{
    python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("result",{{}}).get("root_pane",{{}}).get("pane_id") or d.get("result",{{}}).get("pane",{{}}).get("tab_id"); print(v if v is not None else "null")'
}}
source "{AI_ALIASES}"
{args}
'''
        result = subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env={
                "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                **dict(
                    item.split("=", 1) for item in env_extra.split() if "=" in item
                ),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        calls = log_path.read_text().splitlines() if log_path.exists() else []
        return result, calls


class AiAllDispatchTest(unittest.TestCase):
    def test_no_args_shows_usage_and_no_dispatch(self):
        result, calls = run_ai_all("ai-all")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage: ai-all <prompt>", result.stderr)
        self.assertEqual(calls, [])

    def test_herdr_env_dispatches_to_herdr(self):
        result, calls = run_ai_all(
            '''
            clh() { :; }
            ai-all "hello"
            ''',
            env_extra="HERDR_ENV=1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c.startswith("herdr tab create") for c in calls), calls)

    def test_tmux_dispatches_to_tmux(self):
        result, calls = run_ai_all(
            '''
            _ai_window_base_name() { printf "%s" "repo"; }
            clh() { :; }
            ai-all "hello"
            ''',
            env_extra="TMUX=/tmp/tmux-1000/default,1,0",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c.startswith("tmux new-window") for c in calls), calls)

    def test_no_multiplexer_rejects(self):
        result, calls = run_ai_all('ai-all "hello"')
        self.assertEqual(result.returncode, 1)
        self.assertIn("tmuxまたはHerdr内で実行してください", result.stderr)
        self.assertEqual(calls, [])


class AiAllHerdrTest(unittest.TestCase):
    def test_happy_path_creates_gemini_and_codex_tabs_with_ai_specific_emoji(self):
        result, calls = run_ai_all(
            '''
            clh() { :; }
            _ai_all_herdr "hello world"
            ''',
            env_extra="HERDR_ENV=1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        tab_creates = [c for c in calls if c.startswith("herdr tab create")]
        # _herdr_run_in_new_tab はcwd/label引数付きでtab createを呼ぶ
        self.assertEqual(len(tab_creates), 2, calls)
        self.assertIn("💎repo", tab_creates[0])
        self.assertIn("🪷repo", tab_creates[1])

    def test_current_tab_renamed_with_claude_emoji_before_clh(self):
        result, calls = run_ai_all(
            '''
            clh() { echo "clh-called: $*" >> "$LOG"; }
            _ai_all_herdr "hello"
            ''',
            env_extra="HERDR_ENV=1 HERDR_TAB_ID=t1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rename_idx = next(
            i for i, c in enumerate(calls) if c.startswith("herdr tab rename")
        )
        clh_idx = next(i for i, c in enumerate(calls) if c.startswith("clh-called"))
        self.assertEqual(calls[rename_idx], "herdr tab rename t1 ✴️repo")
        self.assertLess(rename_idx, clh_idx)

    def test_current_tab_id_resolved_via_pane_get_when_herdr_tab_id_unset(self):
        result, calls = run_ai_all(
            '''
            clh() { :; }
            _ai_all_herdr "hello"
            ''',
            env_extra="HERDR_ENV=1 HERDR_PANE_ID=p9",
            pane_get_tab_id="t9",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c.startswith("herdr pane get p9") for c in calls), calls)
        self.assertIn("herdr tab rename t9 ✴️repo", calls)

    def test_tab_rename_failure_is_swallowed_clh_still_runs(self):
        result, calls = run_ai_all(
            '''
            clh() { echo "clh-called: $*" >> "$LOG"; }
            _ai_all_herdr "hello"
            ''',
            env_extra="HERDR_ENV=1 HERDR_TAB_ID=t1",
            tab_rename_exit=1,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c.startswith("clh-called") for c in calls), calls)

    def test_gemini_tab_creation_failure_skips_codex_and_clh(self):
        result, calls = run_ai_all(
            '''
            clh() { echo "clh-called: $*" >> "$LOG"; }
            _ai_all_herdr "hello"
            ''',
            env_extra="HERDR_ENV=1",
            tab_create_exit=1,
        )
        self.assertEqual(result.returncode, 1)
        tab_creates = [c for c in calls if c.startswith("herdr tab create")]
        self.assertEqual(len(tab_creates), 1, calls)
        self.assertFalse(any(c.startswith("clh-called") for c in calls), calls)

    def test_base_name_lookup_failure_returns_error(self):
        result, calls = run_ai_all(
            '_ai_all_herdr "hello"',
            env_extra="HERDR_ENV=1",
            git_name_defined=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("_review_window_git_name が見つかりません", result.stderr)
        self.assertEqual(calls, [])


class AiHerdrCommandTest(unittest.TestCase):
    CASES = [
        ("gemini", "hello", "gmh --approval-mode plan -i hello"),
        ("codex", "hello", "cxh hello"),
    ]

    def test_command_builder_table_driven(self):
        for ai, prompt, expected in self.CASES:
            with self.subTest(ai=ai):
                result, _ = run_ai_all(f'_ai_herdr_command {ai} "{prompt}"')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
                # tmux版と違い "; zsh" サフィックスは付かない
                self.assertNotIn("; zsh", result.stdout)

    def test_unknown_ai_returns_error(self):
        result, _ = run_ai_all('_ai_herdr_command unknown "hello"')
        self.assertEqual(result.returncode, 1)

    def test_prompt_with_special_characters_is_quoted(self):
        result, _ = run_ai_all(
            "_ai_herdr_command gemini \"it's a test; rm -rf /\""
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        prefix = "gmh --approval-mode plan -i "
        self.assertTrue(result.stdout.startswith(prefix), result.stdout)
        quoted_prompt = result.stdout[len(prefix):].rstrip("\n")
        # クォート済みの結果を再度shellに通しても1トークンとして安全に復元できること
        verify = subprocess.run(
            ["zsh", "-fc", f'eval "print -r -- {quoted_prompt}"'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(verify.stdout.strip(), "it's a test; rm -rf /")


if __name__ == "__main__":
    unittest.main()
