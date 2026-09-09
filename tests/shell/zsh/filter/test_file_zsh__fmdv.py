import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT


FILE_FILTER = REPO_ROOT / "shell/zsh/filter/file.zsh"
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH, "zsh required")
class FmdvTest(unittest.TestCase):
    def run_fmdv(self, selection: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "calls.log"
            env = {**os.environ, "FMDV_LOG": str(log), "FMDV_SELECTION": selection}
            script = f'''
                source "{FILE_FILTER}"
                fd() {{
                  print -r -- "FD<$*>" >> "$FMDV_LOG"
                }}
                filter() {{
                  print -r -- "FILTER<$*>" >> "$FMDV_LOG"
                  print -r -- "$FMDV_SELECTION"
                }}
                mdv() {{
                  print -r -- "MDV<$*>" >> "$FMDV_LOG"
                }}
                fmdv
                exit_code=$?
                print -r -- "__STATUS=$exit_code"
            '''
            result = subprocess.run(
                [ZSH, "-fc", script], capture_output=True, text=True, env=env
            )
            calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        status = next(
            line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__STATUS=")
        )
        return result, status, calls

    def test_selected_markdown_is_opened_in_foreground(self):
        result, status, calls = self.run_fmdv("docs/file with spaces.md")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "0", result.stdout)
        self.assertCountEqual(
            calls,
            [
                "FD<-HI -e md>",
                "FILTER<--preview bat --color=always --style=header,grid {}>",
                "MDV<-- docs/file with spaces.md>",
            ],
        )

    def test_empty_selection_does_not_start_mdv(self):
        result, status, calls = self.run_fmdv("")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "1", result.stdout)
        self.assertCountEqual(
            calls,
            [
                "FD<-HI -e md>",
                "FILTER<--preview bat --color=always --style=header,grid {}>",
            ],
        )


if __name__ == "__main__":
    unittest.main()
