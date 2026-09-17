import subprocess
import unittest


from support import REPO_ROOT, sanitized_env

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def run_steps(script_body: str) -> subprocess.CompletedProcess[str]:
    """common.sh を source し、渡された script_body をそのまま実行する。

    results_file は呼び出し側 (script_body) が mktemp で用意し、
    テスト側では中身を tail で出力させて検証する。
    """
    script = (
        "source mac/scripts/common.sh; "
        "results_file=$(mktemp); "
        f"{script_body}\n"
        'summary_status=$?; '
        'print -r -- "SUMMARY_STATUS=$summary_status"; '
        'print -r -- "---RESULTS---"; '
        'cat -- "$results_file"; '
        'rm -f -- "$results_file"'
    )
    return subprocess.run(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env=sanitized_env({"HOME": str(REPO_ROOT), "PATH": SYSTEM_PATH, "LANG": "en_US.UTF-8"}),
        text=True,
        capture_output=True,
        check=False,
    )


class SettingfilesStepRunnerTest(unittest.TestCase):
    """_settingfiles_run_step / _settingfiles_step_summary の挙動を検証する。"""

    def test_all_steps_succeed_reports_zero_failures(self):
        result = run_steps(
            "_settingfiles_step_init \"$results_file\"; "
            "_settingfiles_run_step \"$results_file\" \"step one\" true; "
            "_settingfiles_run_step \"$results_file\" \"step two\" true; "
            "_settingfiles_step_summary \"$results_file\""
        )
        output = result.stdout + result.stderr

        self.assertIn("SUMMARY_STATUS=0", output)
        self.assertIn("2 成功 / 0 失敗", output)

    def test_failed_step_does_not_block_subsequent_steps(self):
        # false で失敗するステップの後にも次のステップが実行される（継続の実証）。
        result = run_steps(
            "_settingfiles_step_init \"$results_file\"; "
            "_settingfiles_run_step \"$results_file\" \"bad step\" false; "
            "_settingfiles_run_step \"$results_file\" \"good step after\" true; "
            "_settingfiles_step_summary \"$results_file\""
        )
        output = result.stdout + result.stderr

        self.assertIn("PASS\tgood step after", output)
        self.assertIn("FAIL\tbad step", output)

    def test_any_failure_makes_summary_return_nonzero(self):
        result = run_steps(
            "_settingfiles_step_init \"$results_file\"; "
            "_settingfiles_run_step \"$results_file\" \"bad step\" false; "
            "_settingfiles_step_summary \"$results_file\""
        )
        output = result.stdout + result.stderr

        self.assertNotIn("SUMMARY_STATUS=0", output)

    def test_multiple_failures_are_all_listed_in_summary(self):
        result = run_steps(
            "_settingfiles_step_init \"$results_file\"; "
            "_settingfiles_run_step \"$results_file\" \"first bad\" false; "
            "_settingfiles_run_step \"$results_file\" \"second bad\" false; "
            "_settingfiles_step_summary \"$results_file\""
        )
        output = result.stdout + result.stderr

        self.assertIn("✗ first bad:", output)
        self.assertIn("✗ second bad:", output)
        self.assertIn("2 失敗", output)

    def test_error_prefixed_stderr_line_is_extracted_as_reason(self):
        script_body = (
            "_settingfiles_step_init \"$results_file\"; "
            "function _failing_with_error_line() { echo 'Error: something broke' >&2; echo 'boom' >&2; return 1; }; "
            "_settingfiles_run_step \"$results_file\" \"errorful step\" _failing_with_error_line; "
            "_settingfiles_step_summary \"$results_file\""
        )
        result = run_steps(script_body)
        output = result.stdout + result.stderr

        self.assertIn("FAIL\terrorful step\tError: something broke", output)
        self.assertIn("✗ errorful step: Error: something broke", output)

    def test_step_name_with_spaces_is_recorded_as_single_entry(self):
        result = run_steps(
            "_settingfiles_step_init \"$results_file\"; "
            "_settingfiles_run_step \"$results_file\" \"step with spaces in name\" false; "
            "_settingfiles_step_summary \"$results_file\""
        )
        output = result.stdout + result.stderr

        self.assertIn("FAIL\tstep with spaces in name\t", output)
        self.assertIn("✗ step with spaces in name:", output)
        # スペースで分割されて複数レコードになっていないこと
        self.assertEqual(output.count("FAIL\t"), 1)


if __name__ == "__main__":
    unittest.main()
