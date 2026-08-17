import unittest

from support import REPO_ROOT


CORE = REPO_ROOT / "ai/common/pr_comment_implement_core.md"


class PrCommentImplementCommentDispositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

    def test_mandatory_disposition_precedes_design_review(self):
        disposition = self.content.index(
            "### Decide whether the comment should be acted on (MANDATORY)"
        )
        design = self.content.index("### Phase 2: Design Review (MANDATORY)")

        self.assertLess(disposition, design)
        self.assertIn("Do not treat the review comment as an implementation order", self.content)

    def test_disposition_requires_repository_evidence(self):
        for evidence in (
            "current behavior in the affected code and its callers",
            "the complete review thread, repository requirements",
            "the closest tests",
            "scope, regression risk",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, self.content)

        self.assertIn("author's role or authority is not evidence", self.content)

    def test_each_disposition_controls_the_next_step(self):
        for disposition in (
            "`implement`",
            "`reject`",
            "`already-satisfied`",
            "`needs-user-decision`",
        ):
            with self.subTest(disposition=disposition):
                self.assertIn(disposition, self.content)

        self.assertIn("`implement` uses\n`NO_CODE_CHANGE=false`", self.content)
        self.assertIn(
            "`reject` and `already-satisfied` use\n`NO_CODE_CHANGE=true`",
            self.content,
        )

    def test_unresolved_disposition_returns_to_the_user_before_design(self):
        unresolved = self.content.index("For `needs-user-decision`, stop before Phase 2")
        design = self.content.index("### Phase 2: Design Review (MANDATORY)")
        contract = self.content[unresolved:design]

        self.assertIn("competing options", contract)
        self.assertIn("evidence for each", contract)
        self.assertIn("Phase 2 must not begin", contract)

    def test_design_template_exposes_disposition_evidence(self):
        design = self.content.index("### Phase 2: Design Review (MANDATORY)")
        implementation = self.content.index("### Phase 3: Implementation")
        template = self.content[design:implementation]

        for field in (
            "### 採否判断",
            "- 判定: 対応する / 対応不要 / 既対応",
            "- 指摘の前提:",
            "- 確認した証拠:",
            "- 判断理由:",
        ):
            with self.subTest(field=field):
                self.assertIn(field, template)

    def test_codex_generated_skill_receives_disposition_contract(self):
        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "### Decide whether the comment should be acted on (MANDATORY)",
            codex_skill,
        )
        self.assertIn("### 採否判断", codex_skill)


if __name__ == "__main__":
    unittest.main()
