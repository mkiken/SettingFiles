import unittest

from support import REPO_ROOT


class UserConfirmationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/claude/_CLAUDE.md").read_text(encoding="utf-8")
        section = content.split("# User Confirmation\n", 1)[1].split("\n# ", 1)[0]
        cls.confirmation = " ".join(section.split())

    def test_statement_phrased_requests_count_as_questions(self):
        self.assertIn("phrased as statements without a question mark", self.confirmation)
        self.assertIn("questions about optional follow-up actions", self.confirmation)


if __name__ == "__main__":
    unittest.main()
