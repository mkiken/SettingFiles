import unittest

from support import REPO_ROOT


INTRO_PATH = REPO_ROOT / "ai/common/config_audit_subagents/intro_default.md"


class DefaultAuditorEvidenceGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = INTRO_PATH.read_text(encoding="utf-8")

    def test_model_capability_requires_workflow_evidence(self):
        self.assertIn("evidence from the affected model and workflow", self.content)
        self.assertIn("observed runs or a controlled comparison", self.content)
        self.assertIn("general capability claim is insufficient", self.content)

    def test_unverified_rule_is_only_a_validation_candidate(self):
        self.assertIn("only as a validation candidate", self.content)
        self.assertIn("not as removable duplication", self.content)

    def test_irreversible_and_external_boundaries_remain_protected(self):
        for boundary in ("delete", "publish", "billing", "deploy", "security", "personal data"):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, self.content)


if __name__ == "__main__":
    unittest.main()
