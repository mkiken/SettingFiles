import unittest

from support import REPO_ROOT

FORMAT = REPO_ROOT / "ai/common/pr_body_format.md"
CORE = REPO_ROOT / "ai/common/pr_create_by_branch_core.md"
BRANCH_PR_TASK = REPO_ROOT / "ai/common/shared_skills/branch-pr-task/SKILL.md"
CODEX_PR_CREATE = REPO_ROOT / "ai/codex/skills/pr-create-by-branch/SKILL.md"
CODEX_PR_BODY = REPO_ROOT / "ai/codex/skills/pr-body/SKILL.md"

HEADING = "### Task-Based Pull Requests"
REFERENCE = "Task-Based Pull Requests section"


def rule_section():
    content = FORMAT.read_text(encoding="utf-8")
    start = content.index(HEADING)
    end = content.index("\n### ", start + 1)
    return content[start:end]


class TaskBasedPrRuleTest(unittest.TestCase):
    def test_body_link_line_format_is_specified(self):
        section = rule_section()
        self.assertIn("- 関連タスク: [<task title>](<task URL>)", section)
        self.assertIn("end of Summary", section)

    def test_comment_confirmation_includes_pr_title_and_url(self):
        section = rule_section()
        self.assertIn("ask the user per task for separate approval of each operation", section)
        self.assertIn("PR title and URL", section)

    def test_status_proposal_and_fallback(self):
        section = rule_section()
        for required in (
            "current status and available transitions",
            "current status (e.g. `対応中 → レビュー待ち`)",
            "continue with the comment confirmation alone",
            "Execute only approved operations",
            "independently re-fetching it",
            "proposed destination for manual change",
            "each operation's failure separately",
        ):
            with self.subTest(required=required):
                self.assertIn(required, section)

    def test_generated_codex_skills_include_task_rule(self):
        for path in (CODEX_PR_CREATE, CODEX_PR_BODY):
            with self.subTest(path=path):
                self.assertIn(rule_section(), path.read_text(encoding="utf-8"))

    def test_detection_requires_explicit_reference(self):
        # ブランチ名からの推測は誤検知で不要なコメント確認を出すため禁止する
        self.assertIn("Never infer it from a branch name", rule_section())

    def test_rule_names_no_specific_tool(self):
        # ツール名を列挙すると汎用性が失われるため、特定ツール名は書かない
        section = rule_section().lower()
        for name in ("wrike", "github", "jira"):
            self.assertNotIn(name, section)

    def test_pr_creation_paths_reference_rule(self):
        for path in (CORE, CODEX_PR_CREATE):
            content = path.read_text(encoding="utf-8")
            self.assertIn(REFERENCE, content, path.name)
            self.assertIn("full post-creation procedure", content, path.name)

    def test_branch_pr_task_delegates_to_pr_create_by_branch(self):
        content = BRANCH_PR_TASK.read_text(encoding="utf-8")
        self.assertIn("`pr-create-by-branch` skill", content)
        self.assertIn("Task-Based Pull Requests", content)
        self.assertIn("full post-creation procedure", content)


if __name__ == "__main__":
    unittest.main()
