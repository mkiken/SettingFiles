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
        for name in ("review", "review-subagents", "review-merge", "review-report", "_review_run"):
            with self.subTest(name=name):
                result = run_zsh(f"typeset -f -- {name} >/dev/null")
                self.assertEqual(result.returncode, 0, result.stderr)


class ReviewLaunchHerdrTest(unittest.TestCase):
    """_review_launch_herdr の専用workspace作成とorchestratorタブ委譲（herdr/下位関数はstub）。"""

    WS_JSON = (
        '{"result":{"workspace":{"workspace_id":"ws1"},'
        '"tab":{"tab_id":"t0"},"root_pane":{"pane_id":"p0"}}}'
    )

    def run_launch(self, create_watcher):
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "calls.log"
            snippet = f'''
LOG="{log}"
herdr() {{
    printf '%s\\n' "$*" >> "$LOG"
    [[ "$1 $2" == "workspace create" ]] && printf '%s' '{self.WS_JSON}'
    return 0
}}
_review_window_git_name() {{ echo "my-branch"; }}
_herdr_wait_shell_ready() {{ printf 'shell_ready %s\\n' "$1" >> "$LOG"; }}
# 実体は test_herdr_run_in_new_tab.py で検証済みなので、ここでは連番tab_idを代入するstubにする
_herdr_run_in_new_tab() {{
    printf 'newtab %s\\n' "$*" >> "$LOG"
    local n=$(grep -c "^newtab " "$LOG")
    [[ -n "${{5:-}}" ]] && _ai_pr_review_assign "$5" "t${{n}}"
}}
_review_launch_herdr {create_watcher} /tmp/run cl-fn gm-fn cx-fn 123
print -r -- "rc=$?"
'''
            result = run_zsh(snippet)
            calls = log.read_text().splitlines() if log.exists() else []
        return result, calls

    def test_creates_per_run_workspace_and_orchestrator_in_root_tab(self):
        result, calls = self.run_launch(create_watcher=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rc=0", result.stdout)
        # レビューごとの専用workspace（review-<ディレクトリ名>）を新規作成する
        creates = [c for c in calls if c.startswith("workspace create ")]
        self.assertEqual(len(creates), 1, calls)
        self.assertIn("--label review-", creates[0])
        # サブタブは3つだけ（orchestratorはworkspaceの初期タブを使うので4つ目は作らない）
        newtabs = [c for c in calls if c.startswith("newtab ")]
        self.assertEqual(len(newtabs), 3, calls)
        # 初期タブ(t0)をorchestratorにラベル付けし、shell-ready後にroot pane(p0)へ_review_watchを投入
        self.assertIn("tab rename t0 🔍orchestrator:my-branch", calls)
        self.assertIn("shell_ready p0", calls)
        watch_runs = [c for c in calls if c.startswith("pane run p0 _review_watch ")]
        self.assertEqual(len(watch_runs), 1, calls)
        self.assertIn("_review_watch /tmp/run", watch_runs[0])
        self.assertIn("claude.md=t1", watch_runs[0])
        self.assertIn("gemini.md=t2", watch_runs[0])
        self.assertIn("codex.md=t3", watch_runs[0])
        # workspace focus後にorchestratorタブ(t0)へフォーカスする
        self.assertIn("workspace focus ws1", calls)
        self.assertIn("tab focus t0", calls)

    def test_no_watcher_when_disabled(self):
        # --no-merge相当: サブタブ3つのみで、初期タブへの投入・ラベル付け・フォーカスはしない
        result, calls = self.run_launch(create_watcher=0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rc=0", result.stdout)
        newtabs = [c for c in calls if c.startswith("newtab ")]
        self.assertEqual(len(newtabs), 3, calls)
        self.assertFalse(any("_review_watch" in c for c in calls), calls)
        self.assertFalse(any(c.startswith("tab rename ") for c in calls), calls)
        self.assertFalse(any(c.startswith("tab focus ") for c in calls), calls)


class ReviewWatchTest(unittest.TestCase):
    """_review_watch の完了待ち→マージ委譲（waitスクリプト呼び出しとcl-review-mergeはstub）。"""

    def run_watch(self, wait_rc, handle_pre=""):
        snippet = f'''
bash() {{ print -r -- "WAIT:$*"; return {wait_rc}; }}
cl-review-merge() {{ print -r -- "MERGE:$1"; }}
{handle_pre}
_review_watch /tmp/run claude.md=t1 gemini.md=t2 codex.md
echo "rc=$?"
'''
        return run_zsh(snippet)

    def test_wait_success_runs_merge_with_liveness_specs(self):
        result = self.run_watch(wait_rc=0)
        self.assertIn("rc=0", result.stdout)
        self.assertIn("--liveness herdr /tmp/run claude.md=t1 gemini.md=t2 codex.md", result.stdout)
        self.assertIn("MERGE:/tmp/run", result.stdout)

    def test_wait_failure_skips_merge(self):
        # rc 2(タイムアウト)は _review_handle_wait_status がそのまま伝播しマージしない
        result = self.run_watch(wait_rc=2)
        self.assertIn("rc=2", result.stdout)
        self.assertNotIn("MERGE:", result.stdout)


class ReviewWatchClosesTabsTest(unittest.TestCase):
    """_review_watch のタブクローズ委譲。成果物出揃い(wait rc 0)がgateで、マージの成否には依存しない。"""

    def run_watch(self, wait_rc=0, specs="claude.md=t1 gemini.md=t2 codex.md",
                  arrived_files=(), confirm_rc=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        run_dir = Path(self.tmp.name)
        for name in arrived_files:
            (run_dir / name).write_text("result")
        # クローズとマージを同一ログへ追記し、順序（クローズがマージより前）も検証できるようにする
        order_log = run_dir / "order.log"
        confirm_stub = ""
        if confirm_rc is not None:
            confirm_stub = f'confirm() {{ print -r -- "CONFIRM:$1"; return {confirm_rc}; }}\n'
        snippet = f'''
bash() {{ print -r -- "WAIT:$*"; return {wait_rc}; }}
cl-review-merge() {{ printf 'MERGE %s\\n' "$1" >> "{order_log}"; }}
_review_close_ai_tabs() {{ printf 'CLOSE %s\\n' "$*" >> "{order_log}"; }}
{confirm_stub}_review_watch "{run_dir}" {specs}
echo "rc=$?"
'''
        result = run_zsh(snippet)
        order = order_log.read_text().splitlines() if order_log.exists() else []
        return result, order

    def test_close_tabs_precedes_merge_when_files_arrived(self):
        result, order = self.run_watch(wait_rc=0)
        self.assertIn("rc=0", result.stdout)
        self.assertEqual(order[0], "CLOSE t1 t2")
        self.assertTrue(order[1].startswith("MERGE "), order)

    def test_close_tabs_independent_of_merge_artifacts(self):
        # report.html/merged.json をgateにしない契約: マージが成果物を作らなくてもクローズ済み。
        # 成果物ファイル(claude.md等)が残っていればマージは review-merge で再実行できる
        result, order = self.run_watch(wait_rc=0)
        self.assertIn("rc=0", result.stdout)
        self.assertIn("CLOSE t1 t2", order)

    def test_close_tabs_not_called_when_files_incomplete_and_merge_confirmed(self):
        # wait rc 3(不揃い)では部分マージを承諾してもクローズしない。未出力AIタブを
        # 手で確認できるよう残す設計のため、この不在は意図的
        result, order = self.run_watch(
            wait_rc=3, arrived_files=("claude.md",), confirm_rc=0,
        )
        self.assertIn("rc=0", result.stdout)
        self.assertFalse(any(line.startswith("CLOSE ") for line in order), order)
        self.assertTrue(any(line.startswith("MERGE ") for line in order), order)

    def test_close_tabs_and_merge_skipped_when_merge_declined(self):
        result, order = self.run_watch(
            wait_rc=3, arrived_files=("claude.md",), confirm_rc=1,
        )
        self.assertIn("rc=1", result.stdout)
        self.assertEqual(order, [])

    def test_close_tabs_not_called_on_timeout(self):
        result, order = self.run_watch(wait_rc=2)
        self.assertIn("rc=2", result.stdout)
        self.assertEqual(order, [])

    def test_specs_without_tab_ids_close_with_no_candidates(self):
        # tmux相当のspec（=なし）ではtab_idを抽出できないため空引数で委譲する
        result, order = self.run_watch(specs="claude.md gemini.md codex.md")
        self.assertIn("rc=0", result.stdout)
        self.assertEqual(order[0], "CLOSE ")


class ReviewCloseAiTabsTest(unittest.TestCase):
    """_review_close_ai_tabs のガード・クローズ処理（herdr/confirmはstub）。確認プロンプトは挟まない。"""

    def run_close(self, tab_ids, current_tab_id="", get_failures=(), close_failures=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        close_log = Path(self.tmp.name) / "close.log"
        args = " ".join(tab_ids)
        get_failures_zsh = " ".join(f'"{t}"' for t in get_failures)
        close_failures_zsh = " ".join(f'"{t}"' for t in close_failures)
        snippet = f'''
GET_FAILURES=({get_failures_zsh})
CLOSE_FAILURES=({close_failures_zsh})
_ai_multiplexer_kind() {{ echo "herdr"; }}
_ai_herdr_current_tab_id() {{ echo "{current_tab_id}"; }}
confirm() {{ print -r -- "CONFIRM:$1"; return 0; }}
herdr() {{
    if [[ "$1 $2" == "tab get" ]]; then
        for f in "${{GET_FAILURES[@]}}"; do [[ "$f" == "$3" ]] && return 1; done
        return 0
    fi
    if [[ "$1 $2" == "tab close" ]]; then
        printf 'CLOSE:%s\\n' "$3" >> "{close_log}"
        for f in "${{CLOSE_FAILURES[@]}}"; do [[ "$f" == "$3" ]] && return 1; done
        return 0
    fi
    return 0
}}
_review_close_ai_tabs {args}
echo "rc=$?"
'''
        result = run_zsh(snippet)
        closed = close_log.read_text().splitlines() if close_log.exists() else []
        return result, closed

    def test_all_candidates_closed_without_confirm(self):
        result, closed = self.run_close(["t1", "t2", "t3"])
        self.assertIn("rc=0", result.stdout)
        self.assertEqual(closed, ["CLOSE:t1", "CLOSE:t2", "CLOSE:t3"])

    def test_confirm_never_invoked(self):
        # 成果物ファイル(claude.md等)の出揃いを呼び出し元が確認済みのため、確認なしで閉じる設計。
        # confirmを復活させるとfreviewのたびに手動応答が必要になるため、不在をピンする
        result, closed = self.run_close(["t1", "t2"])
        self.assertNotIn("CONFIRM:", result.stdout)
        self.assertEqual(closed, ["CLOSE:t1", "CLOSE:t2"])

    def test_self_tab_excluded_from_candidates(self):
        result, closed = self.run_close(["t1", "t2"], current_tab_id="t1")
        self.assertIn("レビュー用のAIタブ（1件）を閉じます。", result.stdout)
        self.assertEqual(closed, ["CLOSE:t2"])

    def test_empty_tab_id_excluded_from_candidates(self):
        result, closed = self.run_close(["t1", ""])
        self.assertIn("レビュー用のAIタブ（1件）を閉じます。", result.stdout)
        self.assertEqual(closed, ["CLOSE:t1"])

    def test_already_closed_tab_skipped(self):
        result, closed = self.run_close(["t1", "t2"], get_failures=["t1"])
        self.assertIn("レビュー用のAIタブ（1件）を閉じます。", result.stdout)
        self.assertEqual(closed, ["CLOSE:t2"])

    def test_no_surviving_candidates_reports_and_skips_close(self):
        result, closed = self.run_close(["t1", "t2"], get_failures=["t1", "t2"])
        self.assertIn("rc=0", result.stdout)
        self.assertIn("レビュー用のAIタブは既にすべて閉じられています。", result.stdout)
        self.assertNotIn("を閉じます。", result.stdout)
        self.assertEqual(closed, [])

    def test_one_close_failure_does_not_stop_the_rest(self):
        result, closed = self.run_close(["t1", "t2"], close_failures=["t1"])
        self.assertIn("rc=0", result.stdout)
        self.assertEqual(closed, ["CLOSE:t1", "CLOSE:t2"])
        self.assertIn("herdr tab closeに失敗しました", result.stderr)

    def test_tmux_multiplexer_is_noop(self):
        snippet = '''
_ai_multiplexer_kind() { echo "tmux"; }
confirm() { print -r -- "CONFIRM:$1"; return 0; }
herdr() { print -r -- "HERDR:$*"; return 0; }
_review_close_ai_tabs t1 t2
echo "rc=$?"
'''
        result = run_zsh(snippet)
        self.assertIn("rc=0", result.stdout)
        self.assertNotIn("CONFIRM:", result.stdout)
        self.assertNotIn("HERDR:", result.stdout)


class ReviewReportTest(unittest.TestCase):
    """review-report のrun_dir解決とreport.html不在時のエラー処理。"""

    def test_review_report_opens_server_for_existing_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "report.html").write_text("<h1>report</h1>")
            nohup_log = run_dir / "nohup.log"
            # nohup...& のリダイレクトはstub自体のstdoutも飲むため、ログファイルへ記録させて検証する
            snippet = f'''
_ai_pr_review_resolve_latest_run_dir() {{ _ai_pr_review_assign "$1" "{run_dir}"; }}
nohup() {{ printf '%s\\n' "$*" >> "{nohup_log}"; }}
review-report 123
echo "rc=$?"
'''
            result = run_zsh(snippet)
            logged = nohup_log.read_text() if nohup_log.exists() else ""
        self.assertIn("rc=0", result.stdout)
        self.assertIn("python3", logged)
        self.assertIn(str(run_dir), result.stdout)

    def test_review_report_errors_when_report_html_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            snippet = f'''
_ai_pr_review_resolve_latest_run_dir() {{ _ai_pr_review_assign "$1" "{run_dir}"; }}
review-report 123
echo "rc=$?"
'''
            result = run_zsh(snippet)
        self.assertIn("rc=1", result.stdout)
        self.assertIn("report.htmlが見つかりません", result.stderr)


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
