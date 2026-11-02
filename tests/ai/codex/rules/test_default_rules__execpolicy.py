import json
import shutil
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env


RULES_PATH = REPO_ROOT / "ai/codex/rules/default.rules"


@unittest.skipUnless(shutil.which("codex"), "codex CLI is required")
class DefaultRulesExecpolicyTest(unittest.TestCase):
    def assert_decisions(self, commands, expected):
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(
                    ["codex", "execpolicy", "check", "--rules", str(RULES_PATH), "--", *command],
                    capture_output=True,
                    text=True,
                    env=sanitized_env(),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout).get("decision"), expected)

    def test_staging_keeps_explicit_paths_allowed_and_broad_staging_forbidden(self):
        self.assert_decisions([["git", "add", "ai/codex/config.toml"]], "allow")
        self.assert_decisions([["git", "add", "-A"], ["git", "add", "."]], "forbidden")

    def test_commits_keep_existing_prefixes_and_allow_hook_bypass(self):
        self.assert_decisions(
            [
                ["git", "commit", "-m", "fix"],
                ["git", "commit", "--message", "changed"],
                ["git", "commit", "-m", "fix", "--no-verify"],
                ["git", "commit", "-m", "changed", "--no-verify"],
                ["git", "commit", "--message", "changed", "--no-verify"],
                ["git", "commit", "-m", "changed", "-n"],
            ],
            "allow",
        )
        # Preserve the existing prefix boundary without adding new permissions.
        self.assert_decisions(
            [
                ["git", "commit", "--no-verify", "-m", "changed"],
                ["git", "commit", "-n", "-m", "changed"],
                ["git", "commit", "--amend", "--no-edit"],
            ],
            None,
        )

    def test_remote_ref_checks_allow_normal_and_upload_pack_forms(self):
        self.assert_decisions(
            [
                ["git", "ls-remote", "origin", "refs/heads/main"],
                ["git", "ls-remote", "origin", "refs/heads/feature/example"],
                ["git", "ls-remote", "--upload-pack=ssh://example", "origin"],
                ["git", "ls-remote", "--upload-pack", "ssh://example", "origin"],
                ["git", "ls-remote", "origin", "--upload-pack=ssh://example"],
            ],
            "allow",
        )
