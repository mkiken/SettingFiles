import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SCRIPT = REPO_ROOT / "mac/scripts/common.sh"

ROLES = ("designer", "implementer")


class ReviewFixAgentGenerationTest(unittest.TestCase):
    """Runs the real generate_review_fix_agents against a fixture tree.

    The fixture copies the real repository fragments into a tempdir and
    reassigns the sourced Repo global, so generation never touches the
    committed outputs.
    """

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.fixture_root = Path(temp_dir.name)

        common_dst = self.fixture_root / "ai/common/review_fix_subagents"
        src_dst = self.fixture_root / "ai/codex/agents_src/review_fix"
        agents_dst = self.fixture_root / "ai/codex/agents"
        common_dst.mkdir(parents=True)
        src_dst.mkdir(parents=True)
        agents_dst.mkdir(parents=True)
        for role in ROLES:
            shutil.copy(
                REPO_ROOT / f"ai/common/review_fix_subagents/{role}_core.md",
                common_dst,
            )
            shutil.copy(
                REPO_ROOT / f"ai/codex/agents_src/review_fix/head_{role}.toml",
                src_dst,
            )

    def run_fn(self, fn: str) -> subprocess.CompletedProcess[str]:
        script = f'''
source "{COMMON_SCRIPT}"
Repo="{self.fixture_root}/"
{fn}
'''
        return subprocess.run(
            ["zsh", "-c", script, "review-fix-agent-generation-test"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def generated_path(self, role: str) -> Path:
        return self.fixture_root / f"ai/codex/agents/review_fix_{role}.toml"

    def test_generates_both_tomls_from_real_fragments(self):
        expected_sandbox = {
            "designer": 'sandbox_mode = "danger-full-access"',
            "implementer": 'sandbox_mode = "workspace-write"',
        }

        result = self.run_fn("generate_review_fix_agents")

        self.assertEqual(result.returncode, 0, result.stderr)
        for role in ROLES:
            with self.subTest(role=role):
                out = self.generated_path(role)
                self.assertTrue(out.exists(), out)
                content = out.read_text(encoding="utf-8")
                lines = content.splitlines()
                self.assertTrue(
                    lines[0].startswith("# GENERATED FILE - do not edit."),
                    lines[0],
                )
                self.assertIn(f'name = "review_fix_{role}"', content)
                self.assertIn(expected_sandbox[role], content)
                self.assertIn("developer_instructions = '''", content)
                self.assertEqual(lines[-1], "'''")

    def test_generation_is_idempotent(self):
        result = self.run_fn("verify_review_fix_agent_generation_idempotency")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Verified idempotent generation for 2 output(s).", result.stdout
        )

    def test_triple_quote_in_fragment_fails_generation(self):
        core = self.fixture_root / "ai/common/review_fix_subagents/designer_core.md"
        core.write_text(
            core.read_text(encoding="utf-8") + "\nbad ''' marker\n",
            encoding="utf-8",
        )

        result = self.run_fn("generate_review_fix_agents")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("''' found in review_fix_designer fragment", result.stderr)
        self.assertFalse(self.generated_path("designer").exists())


if __name__ == "__main__":
    unittest.main()
