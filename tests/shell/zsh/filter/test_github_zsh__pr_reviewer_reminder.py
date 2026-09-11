import subprocess
import unittest

from support import REPO_ROOT

CLAUDE_SH = REPO_ROOT / "shell/common/alias/claude.sh"
GH_ALIASES = REPO_ROOT / "shell/zsh/alias/gh.zsh"
GITHUB_FILTER = REPO_ROOT / "shell/zsh/filter/github.zsh"


def run_zsh(snippet):
    preamble = (
        'EXIT_CODE_SIGINT=130\n'
        f'source "{CLAUDE_SH}"\n'
        f'source "{GH_ALIASES}"\n'
        f'source "{GITHUB_FILTER}"\n'
    )
    return subprocess.run(
        ["zsh", "-c", preamble + snippet],
        capture_output=True,
        text=True,
    )


# br_fmt/_fgbh/ghをfakeへ差し替える。ghはargvをマーカーとしてstderrへ出力し、
# --web系がgh呼び出しの後にリマインドを出す順序と終了コード伝播だけを検証対象にする
FAKE_COMMANDS = '''
br_fmt() {
    printf '%s' "$FAKE_BRANCH"
}
_fgbh() {
    printf '%s' "$FAKE_BRANCH"
}
gh() {
    if [[ "$1 $2" == "pr create" ]]; then
        printf 'GH_CALL %s\\n' "$*" >&2
        return "${FAKE_GH_EXIT:-0}"
    fi
    return 0
}
'''


class FghpcReviewerReminderTest(unittest.TestCase):
    def test_reminder_after_gh_call_on_success(self):
        result = run_zsh(f'{FAKE_COMMANDS}\nFAKE_BRANCH=main fghpc')
        self.assertEqual(result.returncode, 0, result.stderr)
        gh_pos = result.stderr.index("GH_CALL")
        reminder_pos = result.stderr.index("レビュワー設定")
        self.assertLess(gh_pos, reminder_pos)

    def test_no_gh_call_and_no_reminder_when_branch_unselected(self):
        # SIGINT脱出の非回帰: ブランチ未選択時はghも呼ばれず誤リマインドも出ない
        result = run_zsh(f'{FAKE_COMMANDS}\nFAKE_BRANCH="" fghpc')
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("GH_CALL", result.stderr)
        self.assertNotIn("レビュワー設定", result.stderr)

    def test_gh_failure_exit_code_survives_reminder(self):
        # ||return $?の契約: リマインドの終了コード0でgh失敗を潰さない
        result = run_zsh(f'{FAKE_COMMANDS}\nFAKE_BRANCH=main FAKE_GH_EXIT=1 fghpc')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("レビュワー設定", result.stderr)


class FghpchReviewerReminderTest(unittest.TestCase):
    def test_reminder_after_gh_call_on_success(self):
        result = run_zsh(f'{FAKE_COMMANDS}\nFAKE_BRANCH=main fghpch')
        self.assertEqual(result.returncode, 0, result.stderr)
        gh_pos = result.stderr.index("GH_CALL")
        reminder_pos = result.stderr.index("レビュワー設定")
        self.assertLess(gh_pos, reminder_pos)

    def test_no_reminder_when_branch_unselected(self):
        result = run_zsh(f'{FAKE_COMMANDS}\nFAKE_BRANCH="" fghpch')
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("レビュワー設定", result.stderr)


class GhpcReviewerReminderTest(unittest.TestCase):
    def test_reminder_after_gh_call_and_flags_forwarded(self):
        result = run_zsh(f'{FAKE_COMMANDS}\nghpc --base main --head feature')
        self.assertEqual(result.returncode, 0, result.stderr)
        gh_pos = result.stderr.index("GH_CALL")
        reminder_pos = result.stderr.index("レビュワー設定")
        self.assertLess(gh_pos, reminder_pos)
        # 既存フラグの転送に非回帰であることを確認
        gh_call_line = result.stderr.splitlines()[0]
        self.assertIn("--web", gh_call_line)
        self.assertIn('--body=', gh_call_line)
        self.assertIn("--base main", gh_call_line)
        self.assertIn("--head feature", gh_call_line)

    def test_no_reminder_when_gh_fails(self):
        result = run_zsh(f'{FAKE_COMMANDS}\nFAKE_GH_EXIT=1 ghpc')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("レビュワー設定", result.stderr)


class Fghpc2ReviewerReminderTest(unittest.TestCase):
    def test_reminder_exactly_once_via_ghpc_delegation(self):
        # fghpc2はghpcへ委譲するため、リマインドが二重化しないことを固定する
        script = (
            f'{FAKE_COMMANDS}\n'
            'br_fmt() {\n'
            '  if [[ -z "$_PICKER_CALLED" ]]; then\n'
            '    _PICKER_CALLED=1\n'
            '    printf "base"\n'
            '  else\n'
            '    printf "compare"\n'
            '  fi\n'
            '}\n'
            'fghpc2'
        )
        result = run_zsh(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("レビュワー設定"), 1)

    def test_no_reminder_when_first_picker_empty(self):
        script = f'{FAKE_COMMANDS}\nbr_fmt() {{ printf ""; }}\nfghpc2'
        result = run_zsh(script)
        self.assertEqual(result.returncode, 130)
        self.assertNotIn("レビュワー設定", result.stderr)


if __name__ == "__main__":
    unittest.main()
