import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
COMMON_SH = REPO_ROOT / "mac/scripts/common.sh"
SHARED_SKILL = REPO_ROOT / "ai/common/shared_skills/worktree-task"
PLATFORM_LINK_TARGET = Path("../../common/shared_skills/worktree-task")


class WorktreeTaskSkillDeploymentTest(unittest.TestCase):
    def test_selective_platform_links_resolve_to_shared_skill(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                link = REPO_ROOT / f"ai/{platform}/skills/worktree-task"
                self.assertTrue(link.is_symlink())
                self.assertEqual(Path(os.readlink(link)), PLATFORM_LINK_TARGET)
                self.assertEqual(link.resolve(), SHARED_SKILL.resolve())
                self.assertTrue((link / "SKILL.md").is_file())

        # Gemini is intentionally excluded: worktree-task is the selective
        # Claude/Codex shared-skill case, not an all-platform common skill.
        gemini_link = REPO_ROOT / "ai/gemini/skills/worktree-task"
        self.assertFalse(gemini_link.exists())
        self.assertFalse(gemini_link.is_symlink())

    def test_setup_ai_skills_deploys_regular_and_symlinked_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skills_root = root / "skills"
            shared_root = root / "shared"
            destination = root / "destination"
            (skills_root / "regular-skill").mkdir(parents=True)
            (skills_root / "regular-skill/SKILL.md").write_text("regular\n", encoding="utf-8")
            (shared_root / "selective-skill").mkdir(parents=True)
            (shared_root / "selective-skill/SKILL.md").write_text("selective\n", encoding="utf-8")
            (skills_root / "selective-skill").symlink_to(
                Path("../shared/selective-skill"), target_is_directory=True
            )

            shell = "\n".join(
                [
                    f"source {shlex.quote(str(COMMON_SH))}",
                    "setup_ai_skills "
                    f"{shlex.quote(str(destination))} {shlex.quote(str(skills_root))}",
                ]
            )
            result = subprocess.run(
                ["zsh", "-c", shell], capture_output=True, text=True, check=False
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            regular = destination / "regular-skill"
            selective = destination / "selective-skill"
            self.assertTrue(regular.is_symlink())
            self.assertTrue(selective.is_symlink())
            self.assertEqual(regular.resolve(), (skills_root / "regular-skill").resolve())
            self.assertEqual(
                selective.resolve(), (shared_root / "selective-skill").resolve()
            )

    def test_source_maps_distinguish_all_platform_and_selective_sharing(self):
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        improvement_skill = (
            REPO_ROOT / "ai/common/skills/prompt-self-improvement/SKILL.md"
        ).read_text(encoding="utf-8")

        for source, content in (
            ("CLAUDE.md", claude_md),
            ("prompt-self-improvement", improvement_skill),
        ):
            with self.subTest(source=source):
                self.assertIn("ai/common/skills/", content)
                self.assertIn("ai/common/shared_skills/", content)
                self.assertIn("selective", content.lower())


class WorktreeTaskSkillContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (SHARED_SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_metadata_and_ui_configuration_exist(self):
        self.assertIn("name: worktree-task", self.content)
        self.assertIn("$worktree-task <task prompt>", self.content)

        openai_yaml = (SHARED_SKILL / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Worktree Task"', openai_yaml)
        self.assertIn("$worktree-task", openai_yaml)

    def test_worktree_creation_and_state_guards_are_explicit(self):
        for required in (
            "git status --porcelain",
            "Stop if `HEAD` is detached",
            "Record that the final `refs/heads/<task-branch>` is absent",
            "git worktree list --porcelain",
            "Work only inside the recorded task worktree",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_plan_mode_handoff_reinvokes_the_workflow_after_context_reset(self):
        normalized_content = " ".join(self.content.split())
        for required in (
            "When invoked while the active conversation is in plan mode, plan only",
            "Do not record repository state, invoke `wtc`, create a branch or worktree, or edit files",
            "## Worktree Task Handoff",
            "Implementation entry: `$worktree-task <self-contained task prompt>`",
            "Treat the approved plan as the implementation scope and acceptance criteria",
            "Before any repository mutation, load the current `worktree-task` instructions",
            "without relying on planning context outside the approved artifact",
            "Always include the explicit invocation even when implementation may continue",
            "execute the stateful workflow exactly once, only after plan approval",
            "After a context reset, treat the handoff as a fresh explicit invocation",
            "from `Record the original state` through its remaining checkpoints",
        ):
            with self.subTest(required=required):
                self.assertIn(required, normalized_content)

    def test_configured_zsh_functions_use_safe_positional_boundaries(self):
        for required in (
            "zsh -ic 'builtin cd -q -- \"$1\" && type wtc >/dev/null && type wtm >/dev/null' zsh \"$original_path\"",
            "zsh -ic 'builtin cd -q -- \"$1\" && wtc \"$2\" --base \"$3\" --no-cd' zsh \"$original_path\" \"$task_branch\" \"$original_branch\"",
            "zsh -ic 'builtin cd -q -- \"$1\" && wtm \"$2\"' zsh \"$task_path\" \"$original_branch\"",
            "keep the `-c` script literal",
            "pass paths and branches only as positional arguments",
            "Never interpolate task-derived values into the script string",
            "executes exactly `wtc <task-branch> --base <original-branch> --no-cd` semantics",
            "executes exactly `wtm <original-branch>` semantics",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_slug_drives_shared_herdr_tab_label(self):
        normalized_content = " ".join(self.content.split())
        for required in (
            "Load `herdr-tab-label`",
            "using its shared rules",
            "both the branch name and the later tab-label attempt",
            "After validation succeeds",
            "apply `herdr-tab-label` from the invoking path",
            "Use the slug alone—not the `task/` namespace or timestamp",
            "preserves any non-default tab label",
            "continue the implementation",
            "record the validated task worktree for the invoking tab",
            "set_herdr_task_worktree_context",
            "## Clear Herdr task-worktree context",
            "clear_herdr_task_worktree_context",
            "After confirming that the task worktree entry is absent",
        ):
            with self.subTest(required=required):
                self.assertIn(required, normalized_content)

        self.assertNotIn("lowercase ASCII letters, digits, and hyphens only", self.content)
        self.assertNotIn("set_herdr_task_tab_label", self.content)

    def test_any_post_wtc_failure_cleanup_is_fail_safe(self):
        for required in (
            "If it is nonzero, use the failure handling below",
            "never assume a failed `wtc` created nothing",
            "For any failure after the `wtc` invocation",
            "including a nonzero `wtc` exit or subsequent path uniqueness, branch, or `HEAD` validation failure",
            "assume it may have partially created a branch or worktree",
            "Clean up only if all of these facts are proven",
            "The pre-creation check showed `refs/heads/<task-branch>` absent",
            "The task branch ref and candidate worktree `HEAD` both equal",
            "empty `git status --porcelain` output",
            "If any condition is false or cannot be proven, preserve all state",
            "Never delete ambiguous or changed state",
            "Report the exact candidate worktree paths, refs and object IDs",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_confirmation_contract_has_three_exact_two_choice_gates(self):
        for label in (
            "`コミットのみ`",
            "`コミットしない`",
            "`提案を適用`",
            "`自分で解決`",
            "`プッシュする`",
            "`プッシュしない`",
        ):
            with self.subTest(label=label):
                self.assertEqual(self.content.count(label), 1)

        self.assertIn("Do not offer a push choice at this checkpoint", self.content)
        self.assertIn("ask exactly these two authored choices", self.content)

    def test_conflict_handoff_merge_cleanup_and_push_safety_are_explicit(self):
        for required in (
            "git diff --name-only --diff-filter=U",
            "git ls-files -u",
            "preserve the merge state",
            "verify merge and cleanup independently",
            "If the remote is ahead or the histories diverged",
            "Never automatically pull, rebase, merge, or force-push",
            "Immediately before pushing, re-read",
            "require its object ID to equal the pushed local commit",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_non_conflict_wtm_failure_preserves_state_until_retry_is_safe(self):
        normalized_content = " ".join(self.content.split())
        for required in (
            "## Handle other `wtm` failures",
            "Use the conflict workflow below only when they identify unmerged paths",
            "check whether the recorded task commit is already an ancestor",
            "If it is, do not retry the merge",
            "If the task commit is not merged, preserve the invoking worktree, task worktree, and task branch",
            "Record the exact `wtm` failure output",
            "both worktrees' branches, `HEAD` values, `git status --porcelain` output",
            "Report the blocking state and the preserved task path, branch, and commit",
            "Never stash, reset, clean, commit, or otherwise alter unrelated invoking worktree changes",
            "Do not retry automatically",
            "only after the blocker is confirmed resolved",
            "revalidated as clean, attached to the recorded original branch, and safe to merge",
        ):
            with self.subTest(required=required):
                self.assertIn(required, normalized_content)


if __name__ == "__main__":
    unittest.main()
