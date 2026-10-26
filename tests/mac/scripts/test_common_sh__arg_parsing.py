import subprocess
import unittest


from support import REPO_ROOT

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def run_parser(*args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
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
        'print -r -- "REPROMPT=${SETTINGFILES_DIFF_REVIEW_REPROMPT:-<unset>}"; '
        'print -r -- "SKIP=[${SETTINGFILES_SKIP_STEPS-<unset>}]"'
    )
    return subprocess.run(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env={"HOME": str(REPO_ROOT), "PATH": SYSTEM_PATH, "LANG": "en_US.UTF-8", **(extra_env or {})},
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
        self.assertIn("--skip", result.stdout)

    def test_skip_single_step(self):
        result = run_parser("--skip", "brew")

        self.assertIn("STATUS=0", result.stdout)
        self.assertIn("SKIP=[brew]", result.stdout)

    def test_skip_comma_separated_steps(self):
        result = run_parser("--skip", "brew,pipx")

        self.assertIn("STATUS=0", result.stdout)
        self.assertIn("SKIP=[brew pipx]", result.stdout)

    def test_skip_repeated_option_accumulates(self):
        result = run_parser("--skip", "brew", "--skip", "pipx,mdv")

        self.assertIn("STATUS=0", result.stdout)
        self.assertIn("SKIP=[brew pipx mdv]", result.stdout)

    def test_skip_ignores_empty_comma_segments(self):
        result = run_parser("--skip", ",brew,,pipx,")

        self.assertIn("SKIP=[brew pipx]", result.stdout)

    def test_skip_without_value_returns_error_status(self):
        result = run_parser("--skip")

        self.assertIn("STATUS=2", result.stdout)
        self.assertIn("--skip requires a step name", result.stderr)

    def test_skip_followed_by_another_option_does_not_swallow_it(self):
        result = run_parser("--skip", "--reprompt-reviewed")

        self.assertIn("STATUS=2", result.stdout)
        self.assertIn("--skip requires a step name", result.stderr)
        self.assertIn("REPROMPT=<unset>", result.stdout)

    def test_skip_does_not_inherit_environment_variable(self):
        result = run_parser(extra_env={"SETTINGFILES_SKIP_STEPS": "brew"})

        self.assertIn("STATUS=0", result.stdout)
        self.assertIn("SKIP=[]", result.stdout)

    def test_skip_environment_variable_is_replaced_not_merged(self):
        result = run_parser("--skip", "pipx", extra_env={"SETTINGFILES_SKIP_STEPS": "brew"})

        self.assertIn("SKIP=[pipx]", result.stdout)


if __name__ == "__main__":
    unittest.main()
