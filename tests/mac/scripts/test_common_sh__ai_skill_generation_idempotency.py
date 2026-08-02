import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
COMMON_SH = REPO_ROOT / "mac/scripts/common.sh"


def run_helper(shell_body: str) -> subprocess.CompletedProcess:
    script = f"source {shlex.quote(str(COMMON_SH))}\n{shell_body}"
    return subprocess.run(["zsh", "-c", script], capture_output=True, text=True)


class VerifyGeneratorIdempotencyTest(unittest.TestCase):
    def test_stable_generator_runs_twice_and_succeeds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = shlex.quote(str(Path(temp_dir) / "generated.txt"))
            result = run_helper(
                f"""
typeset -g pass_count=0
function stable_generator() {{
  pass_count=$((pass_count + 1))
  print -r -- stable >| {output}
}}
verify_generator_idempotency stable_generator {output}
exit_code=$?
printf 'passes=%s\n' "$pass_count"
exit "$exit_code"
"""
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified idempotent generation for 1 output(s).", result.stdout)
        self.assertIn("passes=2", result.stdout)

    def test_generator_output_change_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = shlex.quote(str(Path(temp_dir) / "generated.txt"))
            result = run_helper(
                f"""
typeset -g pass_count=0
function changing_generator() {{
  pass_count=$((pass_count + 1))
  print -r -- "$pass_count" >| {output}
}}
verify_generator_idempotency changing_generator {output}
"""
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("generated output changed on second pass", result.stderr)

    def test_failure_modes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated.txt"
            output = shlex.quote(str(output_path))
            missing = shlex.quote(str(Path(temp_dir) / "missing.txt"))
            cases = [
                (
                    "first generator failure",
                    "function test_generator() { return 7; }",
                    output,
                    7,
                    "generator failed on first pass",
                ),
                (
                    "second generator failure",
                    f"""
typeset -g pass_count=0
function test_generator() {{
  pass_count=$((pass_count + 1))
  if (( pass_count == 2 )); then
    return 8
  fi
  print -r -- stable >| {output}
}}
""",
                    output,
                    8,
                    "generator failed on second pass",
                ),
                (
                    "hash failure",
                    f"""
function test_generator() {{ print -r -- stable >| {output}; }}
function shasum() {{ return 9; }}
""",
                    output,
                    9,
                    "failed to hash generated output",
                ),
                (
                    "empty hash output",
                    f"""
function test_generator() {{ print -r -- stable >| {output}; }}
function shasum() {{ return 0; }}
""",
                    output,
                    1,
                    "failed to hash generated output",
                ),
                (
                    "missing output",
                    "function test_generator() { :; }",
                    missing,
                    1,
                    "generated output not found after first pass",
                ),
            ]

            for name, setup, target, expected_code, expected_error in cases:
                with self.subTest(name=name):
                    output_path.unlink(missing_ok=True)
                    result = run_helper(
                        f"""
{setup}
verify_generator_idempotency test_generator {target}
"""
                    )
                    self.assertEqual(result.returncode, expected_code, result.stderr)
                    self.assertIn(expected_error, result.stderr)


if __name__ == "__main__":
    unittest.main()
