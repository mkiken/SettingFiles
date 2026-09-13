import re
import unittest

from support import REPO_ROOT


DESCRIPTION_SOURCES = (
    REPO_ROOT / "ai/codex/skills/pr-comment-review/skill_head.md",
    REPO_ROOT / "ai/codex/skills/pr-body/skill_head.md",
    REPO_ROOT / "ai/codex/skills/grilling/SKILL.md",
    REPO_ROOT / "ai/codex/skills/dig/SKILL.md",
    REPO_ROOT / "ai/claude/skills/grilling/SKILL.md",
    REPO_ROOT / "ai/common/skills/fact-based/SKILL.md",
    REPO_ROOT / "ai/gemini/skills/fact-based/skill_head.md",
    REPO_ROOT / "ai/common/shared_skills/worktree-task/SKILL.md",
)


def description(path):
    frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
    match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing one-line description: {path}")
    return match.group(1).strip()


class SkillDescriptionScopeTest(unittest.TestCase):
    def test_target_descriptions_stay_compact(self):
        for path in DESCRIPTION_SOURCES:
            with self.subTest(path=path):
                self.assertLessEqual(len(description(path)), 200)

    def test_confusable_workflows_keep_their_boundary(self):
        review = description(DESCRIPTION_SOURCES[0])
        fact_based = description(DESCRIPTION_SOURCES[5])
        grilling = description(DESCRIPTION_SOURCES[2])
        dig = description(DESCRIPTION_SOURCES[3])

        self.assertIn("without implementing", review)
        self.assertIn("not for local codebase investigation", fact_based)
        self.assertIn("design decisions", grilling)
        self.assertIn("assumptions and risks", dig)


if __name__ == "__main__":
    unittest.main()
