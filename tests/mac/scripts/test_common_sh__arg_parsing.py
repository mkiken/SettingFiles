import subprocess
import unittest


from support import REPO_ROOT

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def run_parser(*args: str) -> subprocess.CompletedProcess[str]:
    """common.sh を source して parse_settingfiles_common_args を直接呼ぶ。

    戻り値を print し、フラグの反映結果も同時に出力させることで、
    終了コードと副作用の両方を1回の実行で検証できるようにする。
    """
    quoted = " ".join(f'"{arg}"' for arg in args)
    script = (
        "source mac/scripts/common.sh; "
        f"parse_settingfiles_common_args mac/update {quoted}; "
        'parse_status=$?; '
        'print -r -- "STATUS=$parse_status"; '
        'print -r -- "REPROMPT=${SETTINGFILES_DIFF_REVIEW_REPROMPT:-<unset>}"'
    )
    return subprocess.run(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env={"HOME": str(REPO_ROOT), "PATH": SYSTEM_PATH, "LANG": "en_US.UTF-8"},
        text=True,
        capture_output=True,
        check=False,
    )


class ParseSettingfilesCommonArgsTest(unittest.TestCase):
    def test_reprompt_reviewed_sets_environment_variable(self):
        result = run_parser("--reprompt-reviewed")
        output = result.stdout + result.stderr

        self.assertIn("STATUS=0", output)
        self.assertIn("REPROMPT=1", output)

    def test_no_reprompt_reviewed_sets_zero(self):
        result = run_parser("--no-reprompt-reviewed")
        output = result.stdout + result.stderr

        self.assertIn("STATUS=0", output)
        self.assertIn("REPROMPT=0", output)

    def test_no_arguments_leaves_variable_unset(self):
        result = run_parser()
        output = result.stdout + result.stderr

        self.assertIn("STATUS=0", output)
        self.assertIn("REPROMPT=<unset>", output)

    def test_unknown_option_returns_error_status(self):
        result = run_parser("--bogus")
        output = result.stdout + result.stderr

        self.assertIn("STATUS=2", output)
        self.assertIn("Unknown option: --bogus", result.stderr)
        # エラー時の usage は stderr 側へ出す
        self.assertIn("--reprompt-reviewed", result.stderr)

    def test_unknown_option_aborts_even_after_valid_flag(self):
        result = run_parser("--reprompt-reviewed", "--bogus")
        output = result.stdout + result.stderr

        self.assertIn("STATUS=2", output)
        self.assertIn("Unknown option: --bogus", result.stderr)

    def test_help_returns_dedicated_status_and_prints_usage_to_stdout(self):
        result = run_parser("--help")

        self.assertIn("STATUS=10", result.stdout)
        self.assertIn("--reprompt-reviewed", result.stdout)
        self.assertIn("--no-reprompt-reviewed", result.stdout)


if __name__ == "__main__":
    unittest.main()
