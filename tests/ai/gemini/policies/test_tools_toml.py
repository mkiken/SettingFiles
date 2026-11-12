import tomllib
import unittest

from support import REPO_ROOT

TOOLS_TOML = REPO_ROOT / "ai/gemini/policies/tools.toml"


class ToolsTomlPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TOOLS_TOML, "rb") as f:
            cls.policy = tomllib.load(f)

    def test_allows_git_merge_base(self):
        rules = [
            rule
            for rule in self.policy.get("rule", [])
            if rule.get("toolName") == "run_shell_command"
            and rule.get("commandPrefix") == "git merge-base"
        ]
        self.assertEqual(len(rules), 1, "Expected exactly one git merge-base rule")
        rule = rules[0]
        self.assertEqual(rule.get("decision"), "allow")
        self.assertEqual(rule.get("priority"), 100)


if __name__ == "__main__":
    unittest.main()
