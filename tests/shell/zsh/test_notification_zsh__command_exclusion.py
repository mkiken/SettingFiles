"""shell/zsh/notification.zsh の NOTIFY_COMMAND_EXCLUDE（通知を出さないコマンド）テスト。"""
import shlex
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env

NOTIFICATION_ZSH = REPO_ROOT / "shell/zsh/notification.zsh"


class NotificationCommandExclusionTest(unittest.TestCase):
    def is_excluded(self, command: str) -> bool:
        script = f"""
add-zsh-hook() {{ :; }}
source {shlex.quote(str(NOTIFICATION_ZSH))}
_notification_is_excluded_command {shlex.quote(command)}
"""
        result = subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env=sanitized_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode == 0

    def test_ais_is_excluded_with_or_without_arguments(self):
        # ais は対話 picker で、中から resume した AI の終了まで長く動くため通知対象にしない
        for command in ("ais", "ais herdr", "/usr/local/bin/ais foo"):
            with self.subTest(command=command):
                self.assertTrue(self.is_excluded(command))

    def test_ordinary_command_is_not_excluded(self):
        self.assertFalse(self.is_excluded("make build"))

    def test_command_with_ais_as_a_later_word_is_not_excluded(self):
        # 判定は先頭語だけで行う。引数に ais を含むだけの通常コマンドまで除外しない
        self.assertFalse(self.is_excluded("echo ais"))


if __name__ == "__main__":
    unittest.main()
