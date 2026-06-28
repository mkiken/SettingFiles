import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_workmux_aliases() -> str:
    return (REPO_ROOT / "shell/zsh/alias/git.zsh").read_text(encoding="utf-8")


def extract_workmux_setup_guard() -> str:
    content = read_workmux_aliases()
    start = content.index("_workmux_ensure_setup() {")
    end = content.index("\n}\n\nwm() {", start)
    return content[start:end]


class WorkmuxSetupGuardTest(unittest.TestCase):
    def test_prompt_detection_requires_manual_setup(self):
        guard = extract_workmux_setup_guard()

        self.assertNotIn("workmux setup </dev/tty", guard)
        self.assertIn("workmux setup --hooks", guard)
        self.assertIn("workmux setup --skills", guard)
        self.assertIn("WORKMUX_SKIP_SETUP_CHECK=1 <cmd>", guard)
        self.assertIn("return 1", guard)

    def test_wm_still_stops_when_setup_guard_fails(self):
        content = read_workmux_aliases()

        self.assertIn("_workmux_ensure_setup || return $?", content)


if __name__ == "__main__":
    unittest.main()
