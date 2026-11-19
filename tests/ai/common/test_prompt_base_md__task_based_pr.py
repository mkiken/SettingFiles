import unittest

from support import REPO_ROOT

BASE = REPO_ROOT / "ai/common/prompt_base.md"
CORE = REPO_ROOT / "ai/common/pr_create_by_branch_core.md"
BRANCH_PR_TASK = REPO_ROOT / "ai/common/shared_skills/branch-pr-task/SKILL.md"
CODEX_AGENTS = REPO_ROOT / "ai/codex/_AGENTS.md"
CODEX_PR_CREATE = REPO_ROOT / "ai/codex/skills/pr-create-by-branch/SKILL.md"

HEADING = "# Task-Based Pull Requests"
REFERENCE = "Task-Based Pull Requests rule"


def rule_section():
    content = BASE.read_text(encoding="utf-8")
    start = content.index(HEADING)
    end = content.index("\n# ", start + 1)
    return content[start:end]


class TaskBasedPrRuleTest(unittest.TestCase):
    def test_body_link_line_format_is_specified(self):
        section = rule_section()
        self.assertIn("- 関連タスク: [<task title>](<task URL>)", section)
        self.assertIn("end of Summary", section)

    def test_comment_confirmation_includes_pr_title_and_url(self):
        section = rule_section()
        self.assertIn("ask the user per task whether to comment", section)
        self.assertIn("PR title and URL", section)

    def test_detection_requires_explicit_reference(self):
        # ブランチ名からの推測は誤検知で不要なコメント確認を出すため禁止する
        self.assertIn("Never infer it from a branch name", rule_section())

    def test_rule_names_no_specific_tool(self):
        # ツール名を列挙すると汎用性が失われるため、特定ツール名は書かない
        section = rule_section().lower()
        for name in ("wrike", "github", "jira"):
            self.assertNotIn(name, section)

    def test_pr_creation_paths_reference_rule(self):
        for path in (CORE, BRANCH_PR_TASK, CODEX_PR_CREATE):
            self.assertIn(REFERENCE, path.read_text(encoding="utf-8"), path.name)

    def test_codex_agents_carries_rule(self):
        self.assertIn(HEADING, CODEX_AGENTS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
