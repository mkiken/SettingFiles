import os
import unittest
from pathlib import Path


from support import REPO_ROOT


SHARED_SKILL = REPO_ROOT / "ai/common/shared_skills/herdr-tab-label"
PLATFORM_LINK_TARGET = Path("../../common/shared_skills/herdr-tab-label")


class HerdrTabLabelSkillDeploymentTest(unittest.TestCase):
    def test_selective_platform_links_resolve_to_shared_skill(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                link = REPO_ROOT / f"ai/{platform}/skills/herdr-tab-label"
                self.assertTrue(link.is_symlink())
                self.assertEqual(Path(os.readlink(link)), PLATFORM_LINK_TARGET)
                self.assertEqual(link.resolve(), SHARED_SKILL.resolve())

        gemini_link = REPO_ROOT / "ai/gemini/skills/herdr-tab-label"
        self.assertFalse(gemini_link.exists())
        self.assertFalse(gemini_link.is_symlink())


class HerdrTabLabelSkillContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (SHARED_SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_skill_owns_slug_and_safe_invocation_rules(self):
        for required in (
            "lowercase ASCII letters, digits, and hyphens only",
            "Do not use a generic name made only of words",
            "If the active collaboration mode forbids side effects",
            "absolute invoking working directory as `task_path`",
            "set_herdr_task_tab_label \"$3\"",
            "preserves any non-default label",
            "Do not retry during later ordinary tasks",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_integrations_reference_the_skill_without_copying_its_procedure(self):
        codex_base = (REPO_ROOT / "ai/codex/codex_base.md").read_text(encoding="utf-8")
        worktree = (
            REPO_ROOT / "ai/common/shared_skills/worktree-task/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("first substantive user task", codex_base)
        self.assertIn("`herdr-tab-label`", codex_base)
        self.assertIn("Load `herdr-tab-label`", worktree)
        for content in (codex_base, worktree):
            self.assertNotIn("set_herdr_task_tab_label", content)
            self.assertNotIn("lowercase ASCII letters, digits, and hyphens only", content)

    def test_openai_interface_matches_skill(self):
        interface = (SHARED_SKILL / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Herdr Tab Label"', interface)
        self.assertIn("$herdr-tab-label", interface)
