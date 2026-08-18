import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "shell/tmux/open-pr-web.sh"
ZSH = shutil.which("zsh")


class OpenPrWebTest(unittest.TestCase):
    def run_script(
        self,
        *,
        gh_exit: int = 0,
        extra_env: dict | None = None,
        stdin: str = "\n",
    ) -> subprocess.CompletedProcess[str]:
        # スクリプト自身が冒頭で export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH" する
        # ため、実行ファイルのstubをPATH経由で差し替えると実物の/opt/homebrew/bin/ghに
        # 負ける。gh() をzsh関数として定義してからsourceする — zsh関数はPATH上の
        # 実行ファイルより優先されるためPATH操作の影響を受けない
        script = f'''\
gh() {{
  if [[ "$1" == "pr" && "$2" == "view" ]]; then
    return "${{GH_EXIT:-0}}"
  fi
  command gh "$@"
}}
source "{SCRIPT}"
'''
        env = {
            **os.environ,
            "GH_EXIT": str(gh_exit),
            **(extra_env or {}),
        }
        return subprocess.run(
            [ZSH, "-c", script],
            env=env,
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def test_success_does_not_pause_and_leaves_mark_empty(self):
        with tempfile.NamedTemporaryFile() as mark:
            result = self.run_script(
                gh_exit=0, extra_env={"HERDR_POPUP_PAUSE_MARK": mark.name}
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(mark.name).stat().st_size, 0)

    def test_failure_writes_mark_and_waits_for_enter(self):
        with tempfile.NamedTemporaryFile() as mark:
            result = self.run_script(
                gh_exit=1,
                extra_env={"HERDR_POPUP_PAUSE_MARK": mark.name},
                stdin="\n",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("Enterで閉じます。", result.stderr)
            self.assertTrue(Path(mark.name).stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
