import re
import unittest

from support import REPO_ROOT


CSS_PATH = REPO_ROOT / "terminal/mdv/mdv-plans.css"

LEVELS = ("h1", "h2", "h3", "h4", "h5", "h6")


def strip_comments(css):
    """CSS コメントを除去する。禁止事項の説明をコメントに書くと、
    素朴な文字列検索がその説明自体を違反として拾ってしまうため。"""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def light_rule(level):
    return re.compile(
        r"^\.markdown-body\s+" + level + r"\s*\{[^}]*\bcolor:\s*(#[0-9a-fA-F]{3,8})",
        re.MULTILINE,
    )


def dark_rule(level):
    return re.compile(
        r"^\[data-theme=\"dark\"\]\s+\.markdown-body\s+"
        + level
        + r"\s*\{[^}]*\bcolor:\s*(#[0-9a-fA-F]{3,8})",
        re.MULTILINE,
    )


class MdvPlansCssTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")
        cls.declarations = strip_comments(cls.css)

    def test_all_six_heading_levels_have_a_light_color(self):
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertRegex(self.css, light_rule(level))

    def test_all_six_heading_levels_have_a_dark_color(self):
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertRegex(self.css, dark_rule(level))

    def test_light_and_dark_colors_differ_per_level(self):
        # 明暗どちらかをコピペしたまま直し忘れると階層色が片テーマで潰れる
        for level in LEVELS:
            with self.subTest(level=level):
                light = light_rule(level).search(self.css).group(1).lower()
                dark = dark_rule(level).search(self.css).group(1).lower()
                self.assertNotEqual(light, dark)

    def test_no_important_declarations(self):
        # mdv は組み込みCSSの後にこれを配信するので !important は不要。
        # 付けると閲覧者側の上書きまで塞いでしまう。
        # コメント本文で !important に言及することはあるので、宣言だけを見る。
        self.assertNotIn("!important", self.declarations)

    def test_dark_selector_does_not_scope_to_body(self):
        # mdts は body に data-theme を置いたが、mdv は documentElement に置く。
        # body スコープのまま移植するとダークテーマだけ無言で効かなくなる。
        self.assertNotIn("body[data-theme=", self.declarations)

    def test_does_not_style_blockquote_or_table(self):
        # mdv 組み込みCSSで十分な要素には触れない（mdts では upstream の
        # rgba が潰れるため上書きが必要だった）
        for selector in ("blockquote", "table"):
            with self.subTest(selector=selector):
                self.assertNotRegex(
                    self.declarations,
                    re.compile(r"\.markdown-body[^{]*\b" + selector + r"\b"),
                )

    def test_inline_code_is_scoped_to_exclude_pre(self):
        # `:not(pre) > code` の限定を外すと、コードブロック内の chroma による
        # トークン別の色が単色に潰れる。インラインコードだけを狙う。
        for rule in re.finditer(
            r"^(\[data-theme=\"dark\"\]\s+)?\.markdown-body[^{]*\bcode\b[^{]*\{",
            self.declarations,
            re.MULTILINE,
        ):
            with self.subTest(rule=rule.group(0).strip()):
                self.assertIn(":not(pre) > code", rule.group(0))

    def test_inline_code_has_both_light_and_dark_colors(self):
        inline_code = re.compile(
            r"^(?P<dark>\[data-theme=\"dark\"\]\s+)?"
            r"\.markdown-body :not\(pre\) > code\s*\{[^}]*\bcolor:\s*(#[0-9a-fA-F]{3,8})",
            re.MULTILINE,
        )
        matches = {bool(m.group("dark")): m.group(2) for m in inline_code.finditer(self.declarations)}
        self.assertIn(False, matches, "light のインラインコード色がない")
        self.assertIn(True, matches, "dark のインラインコード色がない")
        self.assertNotEqual(matches[False].lower(), matches[True].lower())

    def test_no_userstyle_metadata_or_moz_document(self):
        # Stylus 拡張ではなく mdv がサーバー配信するため、UserStyle 用の
        # メタブロックとドメイン限定ラッパは不要
        self.assertNotIn("==UserStyle==", self.css)
        self.assertNotIn("@-moz-document", self.declarations)

    def test_no_hardcoded_personal_paths(self):
        self.assertNotIn("/Users/", self.css)


if __name__ == "__main__":
    unittest.main()
