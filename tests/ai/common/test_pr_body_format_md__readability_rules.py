import unittest

from support import REPO_ROOT

FORMAT = REPO_ROOT / "ai/common/pr_body_format.md"
CODEX_PR_BODY = REPO_ROOT / "ai/codex/skills/pr-body/SKILL.md"
CODEX_PR_CREATE = REPO_ROOT / "ai/codex/skills/pr-create-by-branch/SKILL.md"


def split_sections(content):
    """雛形（```markdown フェンス内）と Rules 本文を分けて返す。

    雛形に見出しがあるかと、Rules に指示があるかは別の主張なので、
    片方の文字列が他方に混ざったまま検証しないよう分離する。
    """
    fence = "````markdown"
    start = content.index(fence) + len(fence)
    end = content.index("````", start)
    return content[start:end], content[end:]


class PrBodyFormatReadabilityRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = FORMAT.read_text(encoding="utf-8")
        cls.template, cls.rules = split_sections(cls.content)

    def test_summary_leads_with_conclusion_within_three_lines(self):
        self.assertIn("conclusion in 3 lines or fewer", self.template)
        self.assertIn("Lead with the conclusion", self.rules)
        self.assertIn("3 lines or fewer", self.rules)

    def test_conclusion_last_construction_is_forbidden(self):
        self.assertIn(
            "never replay the evaluation process and leave the conclusion for the end",
            self.rules,
        )

    def test_alternatives_section_uses_two_column_table(self):
        self.assertIn("## 検討した代替案", self.template)
        self.assertIn("| 案 | 却下理由 |", self.template)
        self.assertIn("two-column table (案 / 却下理由)", self.rules)

    def test_alternatives_prose_pros_and_cons_are_forbidden(self):
        self.assertIn("never write merits and demerits out as prose", self.rules)

    def test_non_viable_alternatives_are_not_given_equal_weight(self):
        self.assertIn(
            "never give an option the requirements rule out from the start "
            "the same weight as the adopted one",
            self.rules,
        )

    def test_out_of_scope_generalities_are_forbidden(self):
        self.assertIn(
            "Do not enumerate out-of-scope generalities or possible future extensions",
            self.rules,
        )

    def test_no_non_goals_section_in_template(self):
        # Non-goals は常設セクションにしない決定を固定する。PR body は設計文書より
        # 短く差分がスコープを自己証明するため、見出しを増やすと「定型見出しを律儀に
        # 埋める」癖を一つ増やすことになる。代わりに上の禁止ルールで対処している。
        self.assertNotIn("## Non-goals", self.template)
        self.assertNotIn("## やらないこと", self.template)

    def test_deletion_criterion_is_given(self):
        self.assertIn(
            'ask "can a reviewer understand the decision without it?"', self.rules
        )
        self.assertIn("if yes, drop it", self.rules)

    def test_boilerplate_sections_are_conditional(self):
        self.assertIn(
            "Write boilerplate sections such as terminology, background, or purpose "
            "only when a reviewer cannot judge the change without them",
            self.rules,
        )

    def test_inapplicable_sections_are_omitted_not_filled(self):
        self.assertIn("Omit any section that does not apply", self.rules)
        for section in ("検討した代替案", "Breaking Changes", "Additional Notes"):
            self.assertIn(section, self.rules)
        self.assertIn('Do not fill a section with "なし" or a placeholder', self.rules)

    def test_breaking_changes_no_longer_prescribes_a_nashi_placeholder(self):
        # 旧仕様の 'if none: "なし"' は「該当なしならセクションごと省略」と矛盾する。
        # 雛形側にプレースホルダ指示が復活していないことを固定する。
        self.assertNotIn('if none: "なし"', self.template)

    def test_review_focus_points_stays_mandatory(self):
        # ここだけは省略可にしない。pr_body_core.md の保全ロジックが
        # 「特になし」を既定値として参照し、既存bodyの非デフォルト内容を
        # 保護する判定に使っているため、常設でないと判定の基準が失われる。
        self.assertIn("## Review Focus Points", self.template)
        self.assertIn("特になし", self.template)
        self.assertIn(
            "Review Focus Points is the exception: always keep it", self.rules
        )

    def test_codex_generated_skills_carry_the_new_rules(self):
        for path in (CODEX_PR_BODY, CODEX_PR_CREATE):
            with self.subTest(path=path.name):
                generated = path.read_text(encoding="utf-8")
                self.assertIn("## 検討した代替案", generated)
                self.assertIn("Lead with the conclusion", generated)


if __name__ == "__main__":
    unittest.main()
