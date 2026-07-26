import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "ai" / "codex" / "hooks" / "codex-stop-notification.sh"


def write_codex_transcript(path: Path, assistant_message: str) -> None:
    events = [
        {
            "timestamp": "2026-07-19T00:00:00.000Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "通知フックを確認して"}],
            },
        },
        {
            "timestamp": "2026-07-19T00:00:01.000Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": assistant_message}],
            },
        },
    ]
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )


class CodexStopNotificationHookTest(unittest.TestCase):
    def run_hook(
        self,
        hook_input: dict,
        assistant_message: str = "対応が完了しました。",
        icon_exit: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], list[str], str]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        common_dir = root / "shell" / "tmux"
        common_dir.mkdir(parents=True)
        event_log = root / "events.log"
        transcript = root / "transcript.jsonl"
        write_codex_transcript(transcript, assistant_message)

        common_header = common_dir / "ai_notification_hook_common.sh"
        common_header.write_text(
            "EMOJI_STATUS_NOTIFICATION='✋'\n"
            "EMOJI_STATUS_COMPLETED='✅'\n"
            "AI_HOOK_EMOJI_ID='🪷'\n"
            "debug_log() { :; }\n"
            "build_ai_title() { printf '%s' \"$2\"; }\n"
            "truncate_line() { printf '%s' \"$1\"; }\n"
            "normalize_oneline() { printf '%s' \"$1\"; }\n"
            "guess_task_type_emoji() { printf '🔧'; }\n"
            "build_session_summary() { printf '%s' \"$2\"; }\n"
            # 実共通ヘッダは ai_notification_sound.sh を source して定義する。
            # フックが $(ai_notification_sound <event>) を呼ぶためモックにも用意する。
            "ai_notification_sound() { printf '%s' \"$1\"; }\n"
            "hook_fallback_notify() { notify fallback \"$1\"; }\n"
            "update_tmux_window_name() {\n"
            "  printf 'icon-start:%s:%s:%s\\n' \"$1\" \"$2\" \"$3\" >> \"$HOOK_TEST_LOG\"\n"
            "  sleep 0.08\n"
            "  printf 'icon-complete:%s\\n' \"$1\" >> \"$HOOK_TEST_LOG\"\n"
            "  if [ \"$HOOK_ICON_EXIT\" -ne 0 ]; then\n"
            "    printf 'stub update failure\\n' >&2\n"
            "    return \"$HOOK_ICON_EXIT\"\n"
            "  fi\n"
            "}\n"
            "notify() { printf 'notify:%s\\n' \"$1\" >> \"$HOOK_TEST_LOG\"; }\n",
            encoding="utf-8",
        )

        input_with_transcript = dict(hook_input)
        input_with_transcript["transcript_path"] = str(transcript)
        input_with_transcript.setdefault("session_id", "notification-test")
        env = os.environ.copy()
        # HERDR_ENV/TMUX系はフック先頭の早期returnガードを誘発し、
        # スタブが呼ばれずevents.logが生成されない実行環境汚染を防ぐ
        for name in ("HERDR_ENV", "TMUX", "TMUX_PANE"):
            env.pop(name, None)
        env.update(
            {
                "SET": f"{root}/",
                "TMPDIR": str(root),
                "HOOK_TEST_LOG": str(event_log),
                "HOOK_ICON_EXIT": str(icon_exit),
            }
        )
        result = subprocess.run(
            ["bash", str(HOOK)],
            cwd=REPO_ROOT,
            env=env,
            input=json.dumps(input_with_transcript, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        events = event_log.read_text(encoding="utf-8").splitlines()
        error_log = root / "codex-stop-notification-error.log"
        errors = error_log.read_text(encoding="utf-8") if error_log.exists() else ""
        return result, events, errors

    def test_icon_completion_precedes_notification_table(self):
        cases = [
            (
                "apply_patch承認待ち",
                {
                    "hook_event_name": "PermissionRequest",
                    "tool_name": "apply_patch",
                    "tool_input": {"command": "*** Begin Patch\n*** Update File: example\n"},
                },
                "対応が完了しました。",
                "✋",
                "承認待ち",
            ),
            (
                "Stop応答待ち",
                {"hook_event_name": "Stop"},
                "この内容で進めてよろしいですか？修正点があれば教えてください。",
                "✋",
                "応答待ち",
            ),
            (
                "Stop完了",
                {"hook_event_name": "Stop"},
                "対応が完了しました。",
                "✅",
                "終了",
            ),
        ]
        for desc, hook_input, assistant_message, emoji, title in cases:
            with self.subTest(desc):
                result, events, errors = self.run_hook(hook_input, assistant_message)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(errors, "")
                self.assertEqual(
                    events,
                    [
                        f"icon-start:{emoji}:🪷:true",
                        f"icon-complete:{emoji}",
                        f"notify:{title}",
                    ],
                )

    def test_icon_failure_is_logged_and_notification_continues(self):
        hook_input = {
            "hook_event_name": "PermissionRequest",
            "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Update File: example\n"},
        }
        result, events, errors = self.run_hook(hook_input, icon_exit=6)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events[-1], "notify:承認待ち")
        self.assertLess(events.index("icon-complete:✋"), events.index("notify:承認待ち"))
        self.assertIn("stub update failure", errors)
        self.assertIn("tmux icon update failed (status=6)", errors)


if __name__ == "__main__":
    unittest.main()
