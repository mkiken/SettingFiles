import unittest

from support import REPO_ROOT


ADAPTERS = {
    "claude pr-review": (REPO_ROOT / "ai/claude/skills/pr-review/SKILL.md", "pr-review-verifier"),
    "claude pr-review-subagents": (REPO_ROOT / "ai/claude/skills/pr-review-subagents/SKILL.md", "pr-review-verifier"),
    "gemini pr-review": (REPO_ROOT / "ai/gemini/commands/pr-review.toml", "pr-review-verifier"),
    "gemini pr-review-subagents": (REPO_ROOT / "ai/gemini/commands/pr-review-subagents.toml", "pr-review-verifier"),
}
CODEX_SKILLS = {
    "codex pr-review": REPO_ROOT / "ai/codex/skills/pr-review/SKILL.md",
    "codex pr-review-subagents": REPO_ROOT / "ai/codex/skills/pr-review-subagents/SKILL.md",
}
VERIFIER_AGENTS = (
    REPO_ROOT / "ai/claude/agents/pr-review-verifier.md",
    REPO_ROOT / "ai/gemini/agents/pr-review-verifier.md",
    REPO_ROOT / "ai/codex/agents/pr_review_verifier.toml",
)


class VerifyStageAdapterTest(unittest.TestCase):
    def test_runtime_adapters_load_stage_and_launch_verifier(self):
        for name, (path, verifier) in ADAPTERS.items():
            with self.subTest(adapter=name):
                content = path.read_text(encoding="utf-8")
                self.assertIn("common/pr_review_verify.md", content)
                self.assertIn(f"**{verifier}**", content)
                self.assertIn("only when findings exist", content)

    def test_generated_codex_skills_embed_stage_and_launch_verifier(self):
        for name, path in CODEX_SKILLS.items():
            with self.subTest(skill=name):
                content = path.read_text(encoding="utf-8")
                self.assertIn("### Verify Findings", content)
                self.assertIn("`pr_review_verifier`", content)
                self.assertIn("only when findings exist", content)

    def test_claude_pr_review_may_launch_subagent(self):
        content = ADAPTERS["claude pr-review"][0].read_text(encoding="utf-8")
        allowed = next(line for line in content.splitlines() if line.startswith("allowed-tools:"))
        self.assertIn("Task", allowed)

    def test_verifier_agents_are_not_limited_to_high_findings(self):
        # Every finding is verified now; a High-only verifier prompt would make it
        # skip or distrust Medium/Low payload entries.
        for path in VERIFIER_AGENTS:
            with self.subTest(path=path):
                self.assertNotIn("High", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
