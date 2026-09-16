import subprocess
import unittest

from support import REPO_ROOT, sanitized_env

GH_ALIASES = REPO_ROOT / "shell/zsh/alias/gh.zsh"


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-c", f'source "{GH_ALIASES}"; {snippet}'],
        capture_output=True,
        text=True,
        env=sanitized_env(),
    )


class StackAliasExpansionTest(unittest.TestCase):
    """gh stack 系aliasの展開内容を固定する。"""

    def test_ghsy_bakes_in_prune_flag(self):
        result = run_zsh("alias ghsy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ghsy='gh stack sync --prune'")

    def test_ghsv_wraps_interactive_view_with_no_notify(self):
        # gh stack view のデフォルトは対話TUIなので gh-dash と同様に no_notify を通す
        result = run_zsh("alias ghsv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ghsv='no_notify gh stack view'")

    def test_ghsvs_short_view_has_no_notify_wrapper(self):
        # --short は非対話の一行出力なので no_notify は不要
        result = run_zsh("alias ghsvs")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ghsvs='gh stack view --short'")
        self.assertNotIn("no_notify", result.stdout)

    def test_no_global_alias_defined_for_stack_prefix(self):
        # alias -g はコマンド行中どこでも展開されるため誤用防止のinvariant
        result = run_zsh("alias -g")
        self.assertEqual(result.returncode, 0, result.stderr)
        stack_global_aliases = [
            line for line in result.stdout.splitlines() if line.startswith("ghs")
        ]
        self.assertEqual(stack_global_aliases, [])


if __name__ == "__main__":
    unittest.main()
