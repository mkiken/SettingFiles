"""terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh の claude+done分岐。

APIエラーで停止したセッションのdoneイベントで、通常の完了通知ではなく
エラー停止の通知（絵文字/ラベル/音がエラー用に切り替わる）が出ることを固定する。
このフックは herdr CLI 呼び出し(pane get/tab get/workspace list)が多いため、
claude+done分岐のtranscript解析サブシェル部分だけを切り出してテストする
（tmux経路 stop-send-notification.sh のフル実行テストと役割分担）。
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT
HOOK = REPO_ROOT / "terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh"


def extract_claude_done_subshell(hook_source: str) -> str:
    """claude+done分岐のサブシェル本体（`claude_pending="$( ... )"`の中身）を抜き出す。

    フック全体はherdr CLI呼び出しが多く単体テストしづらいため、このサブシェルのロジック
    だけを実際のスクリプトから抽出してテストする（コピーではなく実ファイルから抽出する
    ことで、実装とテストの乖離を防ぐ）。
    """
    marker_start = 'claude_pending="$(\n'
    marker_end = '\n  )"'
    start = hook_source.index(marker_start) + len(marker_start)
    end = hook_source.index(marker_end, start)
    return hook_source[start:end]


class ClaudeDoneSubshellTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.subshell_body = extract_claude_done_subshell(HOOK.read_text(encoding="utf-8"))

    def run_subshell(self, transcript_lines: list[str], session_id: str = "s1") -> str:
        transcript_path = self.root / f"{session_id}.jsonl"
        transcript_path.write_text("\n".join(transcript_lines) + "\n", encoding="utf-8")
        projects_dir = self.root / "projects" / "proj"
        projects_dir.mkdir(parents=True, exist_ok=True)
        (projects_dir / f"{session_id}.jsonl").write_text(
            "\n".join(transcript_lines) + "\n", encoding="utf-8"
        )
        script = (
            f'REPO_ROOT="{REPO_ROOT}"\n'
            f'CLAUDE_CONFIG_DIR="{self.root}"\n'
            f'session_id="{session_id}"\n'
            + self.subshell_body
        )
        result = subprocess.run(
            ["zsh", "-c", script], capture_output=True, text=True, check=False
        )
        return result.stdout

    def test_no_error_outputs_pending_only(self):
        output = self.run_subshell(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {"role": "user", "content": "テストして"},
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:01:00.000Z",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "完了しました"}],
                        },
                    }
                ),
            ]
        )
        lines = output.splitlines()
        self.assertEqual(lines[0], "0")  # PENDING_BACKGROUND_WORK
        self.assertEqual(lines[1], "")  # LAST_TURN_API_ERROR

    def test_api_error_outputs_error_type_and_text(self):
        output = self.run_subshell(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "isApiErrorMessage": True,
                        "error": "server_error",
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {
                            "role": "assistant",
                            "stop_reason": "stop_sequence",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "API Error: Connection closed mid-response.",
                                }
                            ],
                        },
                    }
                )
            ]
        )
        lines = output.splitlines()
        self.assertEqual(lines[0], "0")  # PENDING_BACKGROUND_WORK
        self.assertEqual(lines[1], "server_error")  # LAST_TURN_API_ERROR
        self.assertEqual(lines[2], "API Error: Connection closed mid-response.")

    def test_unresolvable_transcript_fails_safe_to_empty_output(self):
        # resolve_host_transcriptが失敗する（該当session_idのtranscriptが存在しない）
        # 場合、サブシェル全体が空出力に落ちる（fail-safe: 呼び出し側は従来どおり
        # 通常の完了通知にフォールバックする）
        script = (
            f'REPO_ROOT="{REPO_ROOT}"\n'
            f'CLAUDE_CONFIG_DIR="{self.root}"\n'
            'session_id="no-such-session-id"\n'
            + self.subshell_body
        )
        result = subprocess.run(["zsh", "-c", script], capture_output=True, text=True, check=False)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
