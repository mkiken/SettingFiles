import re
import unittest


from support import REPO_ROOT

EXPECTED_STEPS = (
    ("editor_configs", "エディタ設定同期"),
    ("git_submodules", "git submodule 更新"),
    ("brew", "Homebrew 更新"),
    ("npm_global", "npm グローバルパッケージ更新"),
    ("pipx", "pipx 更新"),
    ("ai_tools", "AI tools 更新"),
    ("herdr", "Herdr integration 更新"),
    ("mdv", "mdv 更新"),
    ("nvim_plugins", "nvim プラグイン更新"),
    ("znap", "znap pull"),
    ("gh_extensions", "gh extension/skill 更新"),
    ("zcompile", "managed.zsh zcompile"),
)


class MacUpdateStepWiringTest(unittest.TestCase):
    """mac/update の各ステップが _update_run_step（→ _settingfiles_run_step）経由で呼ばれ、
    末尾で _settingfiles_step_summary の結果を終了コードに反映していることを、
    ソース文字列で検証する（実行すると brew/npm/pipx 等に副作用があるため）。
    """

    def setUp(self):
        self.text = (REPO_ROOT / "mac/update").read_text(encoding="utf-8")

    def test_all_steps_are_wired_through_run_step(self):
        for key, step_name in EXPECTED_STEPS:
            with self.subTest(step=key):
                self.assertIn(f'_update_run_step {key} "{step_name}"', self.text)
                self.assertIn(f"function _update_step_{key}()", self.text)

    def test_run_step_helper_dispatches_to_settingfiles_run_step_or_skip(self):
        self.assertIn('_settingfiles_run_step "$_update_results_file" "$step_name" "_update_step_${step_key}"', self.text)
        self.assertIn('_settingfiles_record_skip "$_update_results_file" "$step_name"', self.text)

    def test_skip_keys_are_validated_before_results_file_and_first_step(self):
        validate_call_index = self.text.index("_update_validate_skip_steps ||")
        mktemp_index = self.text.index("_update_results_file=\"$(mktemp")
        first_step_call_index = self.text.index("_update_run_step editor_configs")

        self.assertLess(validate_call_index, mktemp_index)
        self.assertLess(validate_call_index, first_step_call_index)

    def test_tmux_plugin_update_is_not_wired(self):
        self.assertNotIn("_update_step_tmux_plugins", self.text)
        self.assertNotIn("update_plugins", self.text)

    def test_step_functions_do_not_resolve_paths_from_dollar_zero(self):
        # 関数内の $0 は関数名になり dirname が "." を返すため、source が相対パスで失敗する
        function_bodies = re.findall(r"^function _update_step_\w+\(\) \{\n(.*?)^\}", self.text, re.S | re.M)

        self.assertTrue(function_bodies)
        for body in function_bodies:
            self.assertNotIn('"$0"', body)

    def test_ai_and_herdr_steps_source_from_script_dir(self):
        for name in ("claude", "gemini", "codex", "herdr"):
            with self.subTest(script=name):
                self.assertIn(f'source "${{_update_script_dir}}/updates/{name}.sh"', self.text)

    def test_summary_is_called_after_all_steps(self):
        last_step_index = self.text.rindex("_update_run_step ")
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
        first_step_call_index = self.text.index("_update_run_step editor_configs")

        self.assertLess(init_index, first_step_call_index)


if __name__ == "__main__":
    unittest.main()
