import os
import stat
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_review_wait.sh"

# fake herdr: tab get は HERDR_ALIVE_TABS に載っているidのみ成功JSONを返す。
# HERDR_TABGET_FAIL_COUNT=N で最初のN呼び出しを無条件失敗にできる（カウンタは全id共有、
# 単一idのテスト専用）。HERDR_WS_FAIL_COUNT=N で workspace list の最初のN回を失敗させる。
# HERDR_WRITE_ON_TABGET_CALL=N + HERDR_WRITE_FILE で、N回目の tab get 時に結果ファイルを
# 書き出す（exit 3直前の最終再チェックを決定的に検証するためのフック）。
FAKE_HERDR = """#!/bin/bash
case "$1 $2" in
  "tab get")
    id="$3"
    count_file="${HERDR_STATE_DIR}/tabget_count"
    count=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
    printf '%s' "$count" > "$count_file"
    if [[ -n "${HERDR_WRITE_ON_TABGET_CALL:-}" && "$count" -eq "${HERDR_WRITE_ON_TABGET_CALL}" ]]; then
        printf 'result' > "${HERDR_WRITE_FILE}"
    fi
    if [[ "$count" -le "${HERDR_TABGET_FAIL_COUNT:-0}" ]]; then
        echo '{"error":{"code":"unavailable"}}'
        exit 1
    fi
    if grep -qxF "$id" "${HERDR_ALIVE_TABS}" 2>/dev/null; then
        printf '{"result":{"tab":{"tab_id":"%s"}}}' "$id"
        exit 0
    fi
    printf '{"error":{"code":"tab_not_found","message":"tab %s not found"}}' "$id"
    exit 1
    ;;
  "workspace list")
    count_file="${HERDR_STATE_DIR}/ws_count"
    count=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
    printf '%s' "$count" > "$count_file"
    [[ "$count" -le "${HERDR_WS_FAIL_COUNT:-0}" ]] && exit 1
    exit 0
    ;;
esac
exit 0
"""


class AiReviewWaitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = Path(self.tmp.name)

    def run_wait(self, *files, interval="0.05", timeout="1"):
        env = dict(
            os.environ,
            AI_REVIEW_WAIT_INTERVAL=interval,
            AI_REVIEW_WAIT_TIMEOUT=timeout,
        )
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir), *files],
            env=env, capture_output=True, text=True,
        )

    def test_returns_zero_when_all_present(self):
        (self.run_dir / "claude.md").write_text("result")
        (self.run_dir / "codex.md").write_text("result")
        result = self.run_wait("claude.md", "codex.md")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_file_does_not_count_as_done(self):
        (self.run_dir / "claude.md").write_text("")
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)

    def test_times_out_when_file_missing(self):
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("タイムアウト", result.stderr)

    def test_detects_file_created_during_wait(self):
        def create_later():
            time.sleep(0.3)
            (self.run_dir / "claude.md").write_text("result")

        thread = threading.Thread(target=create_later)
        thread.start()
        result = self.run_wait("claude.md", timeout="5")
        thread.join()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_usage_error_without_files(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)


class AiReviewWaitLivenessTest(unittest.TestCase):
    """--liveness herdr でのタブ生死判定（fake herdrをPATH先頭に注入）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = Path(self.tmp.name) / "run"
        self.run_dir.mkdir()
        self.state_dir = Path(self.tmp.name) / "state"
        self.state_dir.mkdir()
        fake_bin = Path(self.tmp.name) / "fake_bin"
        fake_bin.mkdir()
        herdr = fake_bin / "herdr"
        herdr.write_text(FAKE_HERDR)
        herdr.chmod(herdr.stat().st_mode | stat.S_IEXEC)
        self.fake_bin = fake_bin
        self.alive_tabs = Path(self.tmp.name) / "alive_tabs"
        self.alive_tabs.write_text("")

    def run_wait(self, *specs, interval="0.05", timeout="1", extra_env=None):
        env = dict(
            os.environ,
            PATH=f"{self.fake_bin}:{os.environ['PATH']}",
            AI_REVIEW_WAIT_INTERVAL=interval,
            AI_REVIEW_WAIT_TIMEOUT=timeout,
            HERDR_STATE_DIR=str(self.state_dir),
            HERDR_ALIVE_TABS=str(self.alive_tabs),
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["bash", str(SCRIPT), "--liveness", "herdr", str(self.run_dir), *specs],
            env=env, capture_output=True, text=True,
        )

    def test_alive_tab_without_file_times_out(self):
        self.alive_tabs.write_text("t1\n")
        result = self.run_wait("claude.md=t1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("実行中（タブ生存・出力待ち）", result.stderr)

    def test_closed_tab_with_partial_files_returns_3(self):
        (self.run_dir / "codex.md").write_text("result")
        result = self.run_wait("claude.md=t1", "codex.md=t2", timeout="5")
        self.assertEqual(result.returncode, 3)
        self.assertIn("閉鎖✗", result.stderr)
        self.assertIn("閉じられました", result.stderr)
        self.assertIn("完了✓", result.stderr)

    def test_all_closed_without_files_returns_3(self):
        # 0件時の中断/案内は _review_run 側の責務なので、ここではrc 3のみを固定する
        result = self.run_wait("claude.md=t1", "codex.md=t2", timeout="5")
        self.assertEqual(result.returncode, 3)

    def test_file_written_before_close_returns_0(self):
        (self.run_dir / "claude.md").write_text("result")
        result = self.run_wait("claude.md=t1")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_herdr_down_never_marks_closed(self):
        # tab getもプローブ(workspace list)も失敗 → fail-openでタイムアウトに退化
        result = self.run_wait(
            "claude.md=t1", extra_env={"HERDR_WS_FAIL_COUNT": "9999"},
        )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("閉鎖✗", result.stderr)

    def test_mixed_arrival_and_closure_returns_3(self):
        # claudeのタブは生存したまま途中でファイル到着、geminiのタブは閉鎖 → 全体はrc 3
        self.alive_tabs.write_text("t9\n")

        def create_later():
            time.sleep(0.3)
            (self.run_dir / "claude.md").write_text("result")

        thread = threading.Thread(target=create_later)
        thread.start()
        result = self.run_wait("claude.md=t9", "gemini.md=t2", timeout="5")
        thread.join()
        self.assertEqual(result.returncode, 3)
        self.assertIn("完了✓", result.stderr)

    def test_bare_filename_is_never_marked_closed(self):
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("閉鎖✗", result.stderr)
        self.assertIn("実行中（出力待ち）", result.stderr)

    def test_unknown_liveness_backend_is_usage_error(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), "--liveness", "tmux", str(self.run_dir), "claude.md"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)

    def test_empty_handle_degrades_to_no_liveness(self):
        result = self.run_wait("claude.md=")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("閉鎖✗", result.stderr)

    def test_probe_recovery_enables_detection(self):
        # プローブが最初2回失敗する間は確定失敗を数えず、回復後にデバウンス2回で閉鎖検知
        result = self.run_wait(
            "claude.md=t1", timeout="5", extra_env={"HERDR_WS_FAIL_COUNT": "2"},
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("閉鎖✗", result.stderr)

    def test_single_tabget_failure_is_debounced(self):
        # 1回だけの失敗(瞬断)ではmissがリセットされ✗にならない
        self.alive_tabs.write_text("t1\n")
        result = self.run_wait(
            "claude.md=t1", extra_env={"HERDR_TABGET_FAIL_COUNT": "1"},
        )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("閉鎖✗", result.stderr)

    def test_debounce_requires_two_consecutive_failures(self):
        # 1回目の確定失敗では「実行中」のまま、2回目で初めて✗確定
        result = self.run_wait("claude.md=t1", timeout="5")
        self.assertEqual(result.returncode, 3)
        self.assertIn("実行中（タブ生存・出力待ち）", result.stderr)
        self.assertIn("閉鎖✗", result.stderr)

    def test_final_recheck_catches_file_racing_with_closure(self):
        # ✗確定と同じイテレーションでファイルが出現した場合、直前の最終再チェックで拾いrc 0
        target = self.run_dir / "claude.md"
        result = self.run_wait(
            "claude.md=t1", timeout="5",
            extra_env={
                "HERDR_WRITE_ON_TABGET_CALL": "2",
                "HERDR_WRITE_FILE": str(target),
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dashboard_shows_mixed_states(self):
        self.alive_tabs.write_text("t2\n")
        (self.run_dir / "claude.md").write_text("result")
        result = self.run_wait("claude.md=t1", "gemini.md=t2", "codex.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("レビュー完了待ち", result.stderr)
        self.assertIn("完了✓ (claude.md", result.stderr)
        self.assertIn("gemini: 実行中（タブ生存・出力待ち）", result.stderr)
        self.assertIn("codex: 実行中（出力待ち）", result.stderr)


if __name__ == "__main__":
    unittest.main()
