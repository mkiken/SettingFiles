import unittest

from support import REPO_ROOT


CORE_PATH = REPO_ROOT / "ai/common/pr_comment_implement_core.md"
REFERENCE_DIR = REPO_ROOT / "ai/common/pr_comment_implement"


class PrCommentImplementProgressiveDisclosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = " ".join(CORE_PATH.read_text(encoding="utf-8").split())

    def test_entrypoint_routes_each_phase_without_loading_its_procedure(self):
        for reference in (
            "analysis-design.md",
            "implementation.md",
            "finalization.md",
        ):
            with self.subTest(reference=reference):
                self.assertIn(f"`{reference}`", self.core)
                self.assertTrue((REFERENCE_DIR / reference).is_file())

        self.assertNotIn("### Phase 1: Analysis", self.core)
        self.assertNotIn("### Phase 6: Unified Action Selection", self.core)

    def test_entrypoint_preserves_authorization_and_state_boundaries(self):
        for required in (
            "Phase 2 is the only design-approval gate",
            "perform only the deferred 🚀 reaction and worktree creation",
            "skip edits and empty commits",
            "Never infer an unknown authorization or final action",
            "Stop before the affected external action",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.core)

    def test_phase_references_keep_existing_boundaries(self):
        analysis = (REFERENCE_DIR / "analysis-design.md").read_text(encoding="utf-8")
        implementation = (REFERENCE_DIR / "implementation.md").read_text(encoding="utf-8")
        finalization = (REFERENCE_DIR / "finalization.md").read_text(encoding="utf-8")

        self.assertIn("### Phase 1: Analysis", analysis)
        self.assertIn("### Phase 2: Design Review (MANDATORY)", analysis)
        self.assertIn("### Phase 3: Implementation (Only after approval)", implementation)
        self.assertIn("When `NO_CODE_CHANGE=true`, do not edit files or create an empty commit", implementation)
        self.assertIn("### Phase 5: Pre-Action Preparation", finalization)
        self.assertIn("### Phase 6: Unified Action Selection", finalization)
        self.assertIn("### Abort or decline cleanup", finalization)
        self.assertIn("### Verify the final reaction state", finalization)

    def test_platform_adapters_resolve_their_reference_directory(self):
        adapters = {
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/skill_head.md":
                "~/.codex/skills/pr-comment-implement/references",
            REPO_ROOT / "ai/claude/skills/pr-comment-implement/SKILL.md":
                "~/.claude/common/pr_comment_implement",
            REPO_ROOT / "ai/gemini/commands/pr-comment-implement.toml":
                "~/.gemini/common/pr_comment_implement",
        }
        for path, reference_dir in adapters.items():
            with self.subTest(path=path):
                self.assertIn(reference_dir, path.read_text(encoding="utf-8"))

        codex_references = REPO_ROOT / "ai/codex/skills/pr-comment-implement/references"
        self.assertTrue(codex_references.is_symlink())
        self.assertEqual(codex_references.resolve(), REFERENCE_DIR.resolve())


if __name__ == "__main__":
    unittest.main()
