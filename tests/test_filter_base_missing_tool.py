import os
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FILTER_BASE = REPO_ROOT / "shell/zsh/filter/base.zsh"
ZSH = shutil.which("zsh")


class FilterBaseMissingToolTest(unittest.TestCase):
    """filter/base.zsh はzshrc初期化中にsourceされるファイルであり、
    フィルターツールが見つからない場合でもシェル自体を終了させてはならない。

    Herdrのpopup（keys.command）は素のPATH（/usr/bin:/bin:/usr/sbin:/sbin）で
    zsh -ic を起動するため、fzf不在時にexitするとzshrc初期化中にシェルごと
    即死し、popupが一瞬で閉じて -c のコマンドに到達しない。
    """

    def source_base(self, extra_env=None):
        env = {
            **os.environ,
            "TMUX": "",
            "HERDR_ENV": "",
            **(extra_env or {}),
        }
        script = f'''
            source "{FILTER_BASE}"
            print -r -- "__SOURCE_STATUS=$?"
            print -r -- "__SURVIVED=1"
            print -r -- "__FILTER_COMMAND=$FILTER_COMMAND"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            capture_output=True,
            text=True,
            env=env,
        )
        values = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__")
        }
        return result, values

    def test_shell_survives_and_filter_command_setup(self):
        cases = (
            (
                "missing filter tool skips setup without killing the shell",
                {"FILTER_TOOL": "definitely-missing-filter-tool"},
                "",
            ),
            (
                "available filter tool sets FILTER_COMMAND",
                {"FILTER_TOOL": "sh"},
                "sh --cycle --exit-0 --ansi",
            ),
        )
        for description, extra_env, expected_filter_command in cases:
            with self.subTest(description=description):
                result, values = self.source_base(extra_env)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values.get("__SURVIVED"), "1", result.stdout)
                self.assertEqual(values.get("__SOURCE_STATUS"), "0", result.stdout)
                self.assertEqual(
                    values.get("__FILTER_COMMAND"), expected_filter_command
                )


if __name__ == "__main__":
    unittest.main()
