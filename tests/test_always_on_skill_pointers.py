import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# Always-on prompt files: content here loads into every session on the
# platform(s) that read it. Any "load the `X` skill" pointer written here
# must resolve to a real skill, or the pointer silently dangles.
ALWAYS_ON_FILES = [
    REPO_ROOT / "ai/common/prompt_base.md",
    REPO_ROOT / "ai/claude/_CLAUDE.md",
    REPO_ROOT / "ai/gemini/_GEMINI.md",
    REPO_ROOT / "ai/codex/codex_base.md",
]

SKILL_ROOTS = [
    REPO_ROOT / "ai/common/skills",
    REPO_ROOT / "ai/claude/skills",
    REPO_ROOT / "ai/gemini/skills",
    REPO_ROOT / "ai/codex/skills",
]

LOAD_SKILL_PATTERN = re.compile(r"load the `([a-z0-9_-]+)` skill")


class AlwaysOnSkillPointerTest(unittest.TestCase):
    """The always-on prompt layer (prompt_base.md + per-platform entrypoints)
    routes deferrable procedure detail to skills via "load the `X` skill"
    pointers instead of duplicating the procedure inline. Nothing previously
    verified that `X` still exists, or that the section it names still exists
    inside that skill — a renamed skill or renamed heading breaks the pointer
    silently, since the always-on text itself gives no error.
    """

    def test_referenced_skills_exist(self):
        for always_on_file in ALWAYS_ON_FILES:
            text = always_on_file.read_text(encoding="utf-8")
            for skill_name in LOAD_SKILL_PATTERN.findall(text):
                skill_dirs = [root / skill_name for root in SKILL_ROOTS if (root / skill_name / "SKILL.md").is_file()]
                self.assertTrue(
                    skill_dirs,
                    f"{always_on_file.relative_to(REPO_ROOT)} points at the "
                    f"`{skill_name}` skill, but no ai/*/skills/{skill_name}/SKILL.md "
                    "exists in any of ai/common, ai/claude, ai/gemini, ai/codex",
                )

    def test_prompt_self_improvement_has_oip_anchors(self):
        # prompt_base.md's Opportunistic Improvement Proposals rule names
        # this section and two of its subsections by heading text; if any
        # of these headings move or get renamed, the always-on pointer
        # ("follow its 'Opportunistic Improvement Proposals' section") goes
        # stale without any test noticing.
        skill_path = REPO_ROOT / "ai/common/skills/prompt-self-improvement/SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        for anchor in (
            "## Opportunistic Improvement Proposals",
            "### Plan Handoff",
            "## Presenting proposals for approval",
        ):
            self.assertIn(
                anchor,
                text,
                f"ai/common/skills/prompt-self-improvement/SKILL.md is missing "
                f"the '{anchor}' heading that the always-on OIP rule refers to",
            )


if __name__ == "__main__":
    unittest.main()
