import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT

COMMON_SCRIPT = REPO_ROOT / "mac/scripts/common.sh"
ORCHESTRATOR_CORE = REPO_ROOT / "ai/common/pr_review_subagents/orchestrator_core.md"
VERIFIER_CORE = REPO_ROOT / "ai/common/pr_review_subagents/verifier_core.md"

PLATFORMS = ("claude", "gemini", "codex")


class OrchestratorCoreAdversarialVerificationTest(unittest.TestCase):
    def setUp(self):
        self.core = ORCHESTRATOR_CORE.read_text(encoding="utf-8")

    def test_verdict_merge_contract_is_present(self):
        # The downgrade/drop semantics and the summary line are load-bearing for
        # every platform adapter; losing any of them silently changes review output.
        self.assertIn("検証により High 指摘", self.core)
        for verdict in ("confirmed", "unverifiable", "refuted"):
            self.assertIn(verdict, self.core)

    def test_zero_high_findings_skip_is_declared(self):
        self.assertIn("If there are zero High findings, skip this stage entirely", self.core)

    def test_missing_verdict_never_counts_as_confirmed(self):
        self.assertIn("Treat a missing or garbled verdict as unverifiable, never as confirmed", self.core)

    def test_claims_label_in_label_list_and_summary_table(self):
        label_line = next(
            line for line in self.core.splitlines() if line.startswith("Finding-header 領域 labels:")
        )
        self.assertIn("主張検証", label_line)
        table_rows = re.findall(r"^\| (?!領域|-)(\S+) \| N \| XX \|$", self.core, flags=re.MULTILINE)
        self.assertIn("主張検証", table_rows)
        self.assertEqual(len(table_rows), 7)


class VerifierAgentGenerationTest(unittest.TestCase):
    """Runs the real generate_pr_review_verifier_agents against a fixture tree.

    The fixture copies the real repository fragments into a tempdir and
    reassigns the sourced Repo global, so generation never touches the
    committed outputs.
    """

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.fixture_root = Path(temp_dir.name)

        common_dst = self.fixture_root / "ai/common/pr_review_subagents"
        common_dst.mkdir(parents=True)
        shutil.copy(VERIFIER_CORE, common_dst)
        for platform in PLATFORMS:
            src_dst = self.fixture_root / f"ai/{platform}/agents_src/pr_review_verify"
            agents_dst = self.fixture_root / f"ai/{platform}/agents"
            src_dst.mkdir(parents=True)
            agents_dst.mkdir(parents=True)
            head_name = "head_verifier.toml" if platform == "codex" else "head_verifier.md"
            shutil.copy(
                REPO_ROOT / f"ai/{platform}/agents_src/pr_review_verify/{head_name}",
                src_dst,
            )

    def run_fn(self, fn: str) -> subprocess.CompletedProcess[str]:
        script = f'''
source "{COMMON_SCRIPT}"
Repo="{self.fixture_root}/"
{fn}
'''
        return subprocess.run(
            ["zsh", "-c", script, "pr-review-verifier-agent-generation-test"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def generated_path(self, platform: str) -> Path:
        if platform == "codex":
            return self.fixture_root / "ai/codex/agents/pr_review_verifier.toml"
        return self.fixture_root / f"ai/{platform}/agents/pr-review-verifier.md"

    def test_generates_all_platform_agents_from_real_fragments(self):
        result = self.run_fn("generate_pr_review_verifier_agents_all")

        self.assertEqual(result.returncode, 0, result.stderr)
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                out = self.generated_path(platform)
                self.assertTrue(out.exists(), out)
                content = out.read_text(encoding="utf-8")
                self.assertIn("GENERATED FILE - do not edit.", content)
                self.assertIn("adversarial verifier", content)
                if platform == "codex":
                    self.assertIn('name = "pr_review_verifier"', content)
                    self.assertIn("developer_instructions = '''", content)
                    self.assertEqual(content.splitlines()[-1], "'''")
                else:
                    self.assertIn("name: pr-review-verifier", content)

    def test_generation_is_idempotent(self):
        result = self.run_fn("verify_pr_review_verifier_agent_generation_idempotency")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified idempotent generation for 3 output(s).", result.stdout)

    def test_triple_quote_in_core_fails_codex_generation(self):
        core = self.fixture_root / "ai/common/pr_review_subagents/verifier_core.md"
        core.write_text(
            core.read_text(encoding="utf-8") + "\nbad ''' marker\n",
            encoding="utf-8",
        )

        result = self.run_fn("generate_pr_review_verifier_agents codex")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("''' found in pr_review_verifier fragment", result.stderr)
        self.assertFalse(self.generated_path("codex").exists())


if __name__ == "__main__":
    unittest.main()
