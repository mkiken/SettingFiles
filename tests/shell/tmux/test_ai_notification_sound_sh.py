import os
import subprocess
import unittest
from pathlib import Path


from support import REPO_ROOT
SOUND_LIB = REPO_ROOT / "shell/tmux/ai_notification_sound.sh"


def run_sound(event: str) -> subprocess.CompletedProcess:
    """ai_notification_sound.sh を source して ai_notification_sound <event> を呼ぶ。"""
    script = f'source "{SOUND_LIB}"; ai_notification_sound "{event}"'
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, env={**os.environ}
    )


class AiNotificationSoundTest(unittest.TestCase):
    """イベント種別→音名マップ。音はagentではなくイベントで決まる（全AI共通）。"""

    def test_event_to_sound_mapping(self):
        # (イベント, 期待する音名)
        cases = [
            ("completed", "Hero"),
            ("waiting", "Glass"),
            ("error", "Basso"),
            # 未知・空はシステム既定音にフォールバック（fail-safe）
            ("unknown", "default"),
            ("", "default"),
        ]
        for event, expected in cases:
            with self.subTest(event=event):
                result = run_sound(event)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_no_argument_falls_back_to_default(self):
        # 引数なし呼び出しも既定音（*ケース）に落ちる
        script = f'source "{SOUND_LIB}"; ai_notification_sound'
        result = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True, env={**os.environ}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "default")


if __name__ == "__main__":
    unittest.main()
