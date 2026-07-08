import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "shell/common/pr/format_pr_diff_with_line_numbers.sh"


class FormatPrDiffWithLineNumbersTest(unittest.TestCase):
    def run_script(
        self,
        *args: str,
        input_text: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_stdin_formats_current_side_line_numbers(self):
        diff = textwrap.dedent(
            """\
            diff --git a/example.txt b/example.txt
            index 1111111..2222222 100644
            --- a/example.txt
            +++ b/example.txt
            @@ -1,2 +1,2 @@
            -before
            +after
             context
            """
        )

        result = self.run_script("--stdin", input_text=diff)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            textwrap.dedent(
                """\
                FILE example.txt
                @@ -1,2 +1,2 @@
                OLD 1 before
                NEW 1 after
                CTX 2 context
                """
            ),
            result.stdout,
        )

    def test_pr_mode_uses_final_combined_diff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            args_file = temp_path / "gh-args.txt"
            fake_gh = temp_path / "gh"
            fake_gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail

                    printf '%s\\n' "$@" > "${GH_ARGS_FILE}"
                    if [[ " $* " == *" --patch "* ]]; then
                      /bin/cat <<'DIFF'
                    diff --git a/api.go b/api.go
                    index 1111111..2222222 100644
                    --- a/api.go
                    +++ b/api.go
                    @@ -1 +1 @@
                    -func OldAPI() {}
                    +func IntermediateAPI() {}
                    diff --git a/api.go b/api.go
                    index 2222222..3333333 100644
                    --- a/api.go
                    +++ b/api.go
                    @@ -1 +1 @@
                    -func IntermediateAPI() {}
                    +func FinalAPI() {}
                    DIFF
                    else
                      /bin/cat <<'DIFF'
                    diff --git a/api.go b/api.go
                    index 1111111..3333333 100644
                    --- a/api.go
                    +++ b/api.go
                    @@ -1 +1 @@
                    -func OldAPI() {}
                    +func FinalAPI() {}
                    DIFF
                    fi
                    """
                ),
                encoding="utf-8",
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env["PATH"] = f"{temp_path}{os.pathsep}{env['PATH']}"
            env["GH_ARGS_FILE"] = str(args_file)

            result = self.run_script("7359", env=env)

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(
                textwrap.dedent(
                    """\
                    FILE api.go
                    @@ -1 +1 @@
                    OLD 1 func OldAPI() {}
                    NEW 1 func FinalAPI() {}
                    """
                ),
                result.stdout,
            )
            self.assertEqual(
                ["pr", "diff", "7359", "--color=never"],
                args_file.read_text(encoding="utf-8").splitlines(),
            )

    def test_binary_diff_produces_no_false_line_anchors(self):
        diff = textwrap.dedent(
            """\
            diff --git a/logo.png b/logo.png
            index 1111111..2222222 100644
            Binary files a/logo.png and b/logo.png differ
            """
        )

        result = self.run_script("--stdin", input_text=diff)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_submodule_diff_formats_commit_lines(self):
        diff = textwrap.dedent(
            """\
            diff --git a/vendor/library b/vendor/library
            index 1111111..2222222 160000
            --- a/vendor/library
            +++ b/vendor/library
            @@ -1 +1 @@
            -Subproject commit 1111111111111111111111111111111111111111
            +Subproject commit 2222222222222222222222222222222222222222
            """
        )

        result = self.run_script("--stdin", input_text=diff)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            "OLD 1 Subproject commit 1111111111111111111111111111111111111111",
            result.stdout,
        )
        self.assertIn(
            "NEW 1 Subproject commit 2222222222222222222222222222222222222222",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
