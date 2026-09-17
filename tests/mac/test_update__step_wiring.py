import unittest


from support import REPO_ROOT

EXPECTED_STEP_NAMES = (
    "エディタ設定同期",
    "git submodule 更新",
    "Homebrew 更新",
    "tmux プラグイン更新",
    "npm グローバルパッケージ更新",
    "pipx 更新",
    "AI tools 更新",
    "Herdr integration 更新",
    "mdv 更新",
    "nvim プラグイン更新",
    "znap pull",
    "gh extension/skill 更新",
    "managed.zsh zcompile",
)


class MacUpdateStepWiringTest(unittest.TestCase):
    """mac/update の各ステップが _settingfiles_run_step 経由で呼ばれ、
    末尾で _settingfiles_step_summary の結果を終了コードに反映していることを、
    ソース文字列で検証する（実行すると brew/npm/pipx 等に副作用があるため）。
    """

    def setUp(self):
        self.text = (REPO_ROOT / "mac/update").read_text(encoding="utf-8")

    def test_all_steps_are_wired_through_run_step(self):
        for step_name in EXPECTED_STEP_NAMES:
            with self.subTest(step=step_name):
                self.assertIn(f'_settingfiles_run_step "$_update_results_file" "{step_name}"', self.text)

    def test_summary_is_called_after_all_steps(self):
        last_step_index = self.text.rindex("_settingfiles_run_step")
        summary_index = self.text.index("_settingfiles_step_summary")

        self.assertLess(last_step_index, summary_index)

    def test_exit_code_reflects_summary_result(self):
        summary_index = self.text.index("_settingfiles_step_summary")
        status_capture_index = self.text.index("_update_summary_status=$?")
        exit_index = self.text.rindex('exit "$_update_summary_status"')

        self.assertLess(summary_index, status_capture_index)
        self.assertLess(status_capture_index, exit_index)

    def test_results_file_is_initialized_before_any_step_runs(self):
        init_index = self.text.index("_settingfiles_step_init")
        first_step_call_index = self.text.index('_settingfiles_run_step "$_update_results_file"')

        self.assertLess(init_index, first_step_call_index)


if __name__ == "__main__":
    unittest.main()
