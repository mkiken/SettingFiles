import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "shell/tmux/herdr-split-snapshot-pane.sh"
WAIT_HELPER = REPO_ROOT / "shell/tmux/herdr_wait_shell_ready.sh"

# _herdr_wait_shell_ready の1attemptあたりのwaitタイムアウト（共有ヘルパーと一致させる）
ATTEMPT_TIMEOUT_MS = 800
# デフォルト総予算24000msでの最大attempt数
DEFAULT_MAX_ATTEMPTS = 30

HERDR_STUB = """#!/bin/bash
printf '%s\\n' "$*" >> "$HERDR_LOG"
case "$1 $2" in
  "pane split")
    if [[ "${SPLIT_EXIT:-0}" -ne 0 ]]; then
      exit "$SPLIT_EXIT"
    fi
    printf '%s' "$SPLIT_JSON"
    ;;
  "pane run")
    exit 0
    ;;
  "pane wait-output")
    wait_count=$(( $(cat "$WAIT_COUNT_FILE" 2>/dev/null || echo 0) + 1 ))
    printf '%s' "$wait_count" > "$WAIT_COUNT_FILE"
    if (( wait_count <= ${WAIT_FAILURES:-0} )); then
      [[ -n "${WAIT_STDERR:-}" ]] && printf '%s\\n' "$WAIT_STDERR" >&2
      exit 1
    fi
    exit "${WAIT_EXIT:-0}"
    ;;
esac
"""


def run_snapshot_script(
    args: list[str],
    *,
    active_pane_id: str | None = "w1:p1",
    split_exit: int = 0,
    split_json: str = '{"result":{"pane":{"pane_id":"w1:p9"}}}',
    wait_failures: int = 0,
    wait_exit: int = 0,
    wait_stderr: str = "",
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """実行可能スタブのherdrをPATH先頭に置いてスクリプトを実行し、(結果, herdr呼び出しログ) を返す。

    pane wait-output stubは最初の wait_failures 回は exit 1（タイムアウト）を返し、
    それ以降は wait_exit を返す（リトライループの検証用）。
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        log_path = temp_path / "herdr_calls.log"
        wait_count_path = temp_path / "wait_count"
        fake_bin = temp_path / "fake_bin"
        fake_bin.mkdir()
        stub = fake_bin / "herdr"
        stub.write_text(HERDR_STUB)
        stub.chmod(0o755)

        env = {
            "PATH": f"{fake_bin}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": temp_dir,
            "HERDR_LOG": str(log_path),
            "WAIT_COUNT_FILE": str(wait_count_path),
            "SPLIT_EXIT": str(split_exit),
            "SPLIT_JSON": split_json,
            "WAIT_FAILURES": str(wait_failures),
            "WAIT_EXIT": str(wait_exit),
            "WAIT_STDERR": wait_stderr,
        }
        if active_pane_id is not None:
            env["HERDR_ACTIVE_PANE_ID"] = active_pane_id

        result = subprocess.run(
            ["bash", str(SNAPSHOT_SCRIPT), *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        calls = log_path.read_text().splitlines() if log_path.exists() else []
        return result, calls


def run_wait_helper(args: str, *, wait_failures: int = 0) -> tuple[subprocess.CompletedProcess, list[str]]:
    """共有ヘルパーをbashでsourceし、herdrシェル関数モックで _herdr_wait_shell_ready を検証する。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "herdr_calls.log"
        wait_count_path = Path(temp_dir) / "wait_count"
        script = f'''
herdr() {{
    printf '%s\\n' "$*" >> "{log_path}"
    if [[ "$1 $2" == "pane wait-output" ]]; then
        local wait_count=$(( $(cat "{wait_count_path}" 2>/dev/null || echo 0) + 1 ))
        printf '%s' "$wait_count" > "{wait_count_path}"
        (( wait_count <= {wait_failures} )) && return 1
        return 0
    fi
    return 0
}}
source "{WAIT_HELPER}"
_herdr_wait_shell_ready {args}
'''
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=REPO_ROOT,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            text=True,
            capture_output=True,
            check=False,
        )
        calls = log_path.read_text().splitlines() if log_path.exists() else []
        return result, calls


def marker_runs(calls: list[str]) -> list[str]:
    return [c for c in calls if c.startswith("pane run") and "print -r -- __herdr_ready_" in c]


def read_runs(calls: list[str]) -> list[str]:
    return [c for c in calls if c.startswith("pane run") and "pane read" in c]


class TestHerdrSplitSnapshotPane(unittest.TestCase):
    def test_direction_down_passed_to_split(self):
        result, calls = run_snapshot_script(["down"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls[0],
            "pane split --pane w1:p1 --direction down --ratio 0.5 --focus",
        )

    def test_direction_right_passed_to_split(self):
        result, calls = run_snapshot_script(["right"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls[0],
            "pane split --pane w1:p1 --direction right --ratio 0.5 --focus",
        )

    def test_invalid_direction_fails_without_herdr_calls(self):
        result, calls = run_snapshot_script(["diagonal"])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_missing_direction_fails_without_herdr_calls(self):
        result, calls = run_snapshot_script([])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_missing_active_pane_id_fails_without_herdr_calls(self):
        result, calls = run_snapshot_script(["down"], active_pane_id=None)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_empty_active_pane_id_fails_without_herdr_calls(self):
        result, calls = run_snapshot_script(["down"], active_pane_id="")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_subsequent_calls_target_extracted_pane_id(self):
        result, calls = run_snapshot_script(
            ["down"], split_json='{"result":{"pane":{"pane_id":"w3:p42"}}}'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for call in calls[1:]:
            self.assertTrue(
                call.startswith("pane run w3:p42") or call.startswith("pane wait-output w3:p42"),
                call,
            )

    def test_split_failure_stops_before_wait(self):
        result, calls = run_snapshot_script(["down"], split_exit=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_null_pane_id_stops_before_wait(self):
        result, calls = run_snapshot_script(["down"], split_json='{"result":{}}')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_split_token_marker_and_wait_precede_read_command(self):
        result, calls = run_snapshot_script(["down"])
        self.assertEqual(result.returncode, 0, result.stderr)

        markers = marker_runs(calls)
        reads = read_runs(calls)
        self.assertEqual(len(markers), 1)
        self.assertEqual(len(reads), 1)
        self.assertLess(calls.index(markers[0]), calls.index(reads[0]))

        # 送信は分割形（head""tail）、waitのmatchは連結形（実行出力にしか現れない）
        marker_head = markers[0].split("print -r -- ")[1].split('""')[0]
        waits = [c for c in calls if c.startswith("pane wait-output")]
        self.assertEqual(len(waits), 1)
        self.assertIn(f"--match {marker_head}_ok__", waits[0])

    def test_retry_resends_marker_until_wait_succeeds(self):
        result, calls = run_snapshot_script(["down"], wait_failures=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(marker_runs(calls)), 3)
        self.assertEqual(len(read_runs(calls)), 1)

    def test_wait_exhaustion_skips_read_and_fails(self):
        result, calls = run_snapshot_script(["down"], wait_failures=DEFAULT_MAX_ATTEMPTS + 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(marker_runs(calls)), DEFAULT_MAX_ATTEMPTS)
        self.assertEqual(read_runs(calls), [])

    def test_read_command_targets_source_pane_with_less(self):
        result, calls = run_snapshot_script(["down"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            read_runs(calls)[0],
            "pane run w1:p9 herdr pane read w1:p1 --source recent --lines 5000 --format text | less -R +G",
        )


class TestWaitHelperUnderBash(unittest.TestCase):
    """共有ヘルパーがbashでsourceできることと、attempt数の境界値を検証する。"""

    def test_timeout_1600ms_yields_two_attempts(self):
        result, calls = run_wait_helper("w1:p2 1600", wait_failures=DEFAULT_MAX_ATTEMPTS + 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(marker_runs(calls)), 2)

    def test_timeout_1601ms_yields_three_attempts(self):
        result, calls = run_wait_helper("w1:p2 1601", wait_failures=DEFAULT_MAX_ATTEMPTS + 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(marker_runs(calls)), 3)

    def test_succeeds_on_first_ready(self):
        result, calls = run_wait_helper("w1:p2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(marker_runs(calls)), 1)


if __name__ == "__main__":
    unittest.main()
