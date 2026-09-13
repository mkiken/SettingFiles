import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/skills/plan-review/references/browser.md"


class BrowserViewerLifecycleTest(unittest.TestCase):
    def test_uses_reported_port_and_user_driven_shutdown(self):
        content = " ".join(PATH.read_text(encoding="utf-8").split())
        self.assertIn("Never search for a free port first", content)
        self.assertIn("Parse the real URL printed on startup", content)
        self.assertIn("after the user finishes", content)
        self.assertIn("Never close it on a timer", content)


if __name__ == "__main__":
    unittest.main()
