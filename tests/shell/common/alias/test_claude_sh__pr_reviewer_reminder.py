import subprocess
import unittest

from support import REPO_ROOT

CLAUDE_SH = REPO_ROOT / "shell/common/alias/claude.sh"


def run_bash(snippet):
    return subprocess.run(
        ["bash", "-c", f'source "{CLAUDE_SH}"; {snippet}'],
        capture_output=True,
        text=True,
    )


# br_fmt/gh/cloをすべてfakeへ差し替える。argvや通過をマーカーとしてstderrへ出力し、
# 呼び出し順序と終了コードの伝播だけを検証対象にする
FAKE_COMMANDS = '''
br_fmt() {
    echo "main"
}
gh() {
    if [[ "$1 $2" == "pr create" ]]; then
        [[ -n "$FAKE_GH_CREATE_EXIT" ]] && return "$FAKE_GH_CREATE_EXIT"
        return 0
    fi
    if [[ "$1 $2" == "pr view" ]]; then
        [[ -n "$FAKE_GH_VIEW_EXIT" ]] && return "$FAKE_GH_VIEW_EXIT"
        echo "42"
        return 0
    fi
    return 0
}
clo() {
    printf 'CLO_CALL %s\\n' "$*" >&2
    return "${FAKE_CLO_EXIT:-0}"
}
'''


class ClPrCreateReviewerReminderTest(unittest.TestCase):
    def test_reminder_has_no_args_and_writes_to_stderr(self):
        result = run_bash('pr_reviewer_reminder')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("レビュワー設定", result.stderr)

    def test_reminder_stdout_is_empty(self):
        # stderr限定の契約を固定する: 将来コマンド置換で呼ばれてもstdoutを汚さないこと
        result = run_bash('pr_reviewer_reminder')
        self.assertEqual(result.stdout, "")

    def test_reminder_sourced_under_bash_succeeds(self):
        # shell/bash/managed.baがこのファイルをsourceするため、bash互換性を固定する
        result = run_bash('true')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reminder_prints_after_ai_session_completes(self):
        result = run_bash(f'{FAKE_COMMANDS}\ncl-pr-create "title"')
        self.assertEqual(result.returncode, 0, result.stderr)
        clo_pos = result.stderr.index("CLO_CALL")
        reminder_pos = result.stderr.index("レビュワー設定")
        self.assertLess(clo_pos, reminder_pos)

    def test_returns_zero_when_ai_session_succeeds(self):
        result = run_bash(f'{FAKE_COMMANDS}\ncl-pr-create "title"')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ai_session_exit_code_survives_reminder(self):
        # リマインドの終了コード(常に0)でAIセッションの失敗を潰さないことを固定する
        result = run_bash(f'{FAKE_COMMANDS}\nFAKE_CLO_EXIT=3 cl-pr-create "title"')
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("レビュワー設定", result.stderr)

    def test_no_reminder_when_pr_create_fails(self):
        # PRが存在しないのでリマインドは不要
        result = run_bash(f'{FAKE_COMMANDS}\nFAKE_GH_CREATE_EXIT=1 cl-pr-create "title"')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("レビュワー設定", result.stderr)

    def test_empty_title_shows_usage_without_reminder(self):
        result = run_bash(f'{FAKE_COMMANDS}\ncl-pr-create ""')
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)
        self.assertNotIn("レビュワー設定", result.stderr)

    def test_no_reminder_when_pr_number_lookup_fails(self):
        result = run_bash(f'{FAKE_COMMANDS}\nFAKE_GH_VIEW_EXIT=1 cl-pr-create "title"')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("レビュワー設定", result.stderr)


if __name__ == "__main__":
    unittest.main()
