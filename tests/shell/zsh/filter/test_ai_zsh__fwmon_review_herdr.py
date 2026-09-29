"""Legacy fwmon review starts in a named Herdr workspace."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


AI_FILTER = REPO_ROOT / "shell/zsh/filter/ai.zsh"


class FwmonReviewHerdrTest(unittest.TestCase):
    def run_review(self, reused):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "calls"
            fake = root / "herdr"
            fake.write_text(
                "#!/bin/bash\n"
                "printf '%s\\n' \"$*\" >> \"$TEST_CALLS\"\n"
                "case \"$1 $2\" in\n"
                "  'workspace list') printf '%s\\n' \"$TEST_LIST\" ;;\n"
                "  'workspace create') printf '{\"result\":{\"workspace\":{\"workspace_id\":\"new\"},\"root_pane\":{\"pane_id\":\"p0\"}}}\\n' ;;\n"
                "  'tab create') printf '{\"result\":{\"root_pane\":{\"pane_id\":\"p1\"}}}\\n' ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            listing = (
                '{"result":{"workspaces":[{"workspace_id":"old","label":"[1] review","number":1,"focused":false}]}}'
                if reused else '{"result":{"workspaces":[]}}'
            )
            env = sanitized_env({
                "SET": str(REPO_ROOT),
                "PATH": f"{root}{os.pathsep}{os.environ['PATH']}",
                "HERDR_BIN_PATH": str(fake),
                "TEST_CALLS": str(log),
                "TEST_LIST": listing,
            })
            snippet = f'''
source "{AI_FILTER}"
_filter_zoxide_git_worktree_path() {{ print -r -- /tmp/worktree; }}
_review_window_git_name() {{ print -r -- branch; }}
_ai_review_command() {{ print -r -- review-command; }}
_herdr_wait_shell_ready() {{ return 0; }}
_fwmon_review_herdr review
print -r -- "rc=$?"
'''
            result = subprocess.run(
                ["/bin/zsh", "-fc", snippet], env=env, text=True, capture_output=True,
            )
            calls = log.read_text().splitlines() if log.exists() else []
        return result, calls

    def test_new_space_uses_initial_pane(self):
        result, calls = self.run_review(reused=False)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(calls[0], "workspace list")
        self.assertIn("workspace create --label review --cwd /tmp/worktree --no-focus", calls)
        self.assertIn("pane run p0 review-command", calls)
        self.assertFalse(any(call.startswith("tab create") for call in calls))

    def test_existing_space_adds_review_tab(self):
        result, calls = self.run_review(reused=True)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(calls[0], "workspace list")
        self.assertIn("tab create --workspace old --cwd /tmp/worktree --label branch --no-focus", calls)
        self.assertIn("pane run p1 review-command", calls)
        self.assertFalse(any(call.startswith("workspace create") for call in calls))


if __name__ == "__main__":
    unittest.main()
