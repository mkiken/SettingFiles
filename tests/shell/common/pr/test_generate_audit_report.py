import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "generate_audit_report.py"

spec = importlib.util.spec_from_file_location("generate_audit_report", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CATEGORIES = ["default", "overlap", "patch", "ambiguity", "concise", "conflict"]


def audit(items, **overrides):
    data = {
        "schema_version": 1,
        "platform": "Claude Code",
        "platform_key": "claude",
        "scope": "all",
        "source_file_mode": True,
        "run_dir": "/tmp/run",
        "generated_at": "2026-09-01T11:30:00+09:00",
        "manifest": [{"file": "~/.claude/CLAUDE.md", "type": "entry", "note": ""}],
        "summary": {},
        "items": items,
    }
    data.update(overrides)
    return data


def item(id_, **overrides):
    base = {
        "id": id_,
        "category": "default",
        "file": "ai/common/prompt_base.md",
        "section": "## Output Rules",
        "targets": [{"file": "ai/common/prompt_base.md", "section": "## Output Rules"}],
        "summary": "ルール要約",
        "quote": "対象ルールの原文",
        "details": [{"label": "理由", "text": "既定挙動と重複するため"}],
        "depends_on": [],
        "diff": None,
        "estimated_reduction": None,
    }
    base.update(overrides)
    return base


class RenderCategoriesTest(unittest.TestCase):
    def test_every_category_label_is_defined_in_the_renderer(self):
        # カテゴリがレンダラの表に無いと生の文字列で描画されるため、6値すべてを固定する
        for category in CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(f'"{category}"', mod.HTML_TEMPLATE)

    def test_render_embeds_each_item_category(self):
        data = audit([item(i + 1, category=c) for i, c in enumerate(CATEGORIES)])
        html = mod.render(data)
        payload = json.loads(html.split("const DATA = ")[1].split(";\nconst state")[0].replace("<\\/", "</"))
        self.assertEqual([i["category"] for i in payload["items"]], CATEGORIES)

    def test_render_escapes_closing_script_tag(self):
        data = audit([item(1, summary="</script> を含む要約")])
        html = mod.render(data)
        self.assertNotIn("</script> を含む要約", html)
        self.assertIn("<\\/script>", html)


class DetailsAndReductionTest(unittest.TestCase):
    def test_details_survive_rendering_in_declared_order(self):
        details = [
            {"label": "現状", "text": "冗長な表現"},
            {"label": "短縮案", "text": "簡潔な表現"},
            {"label": "削減見込み", "text": "約12語"},
        ]
        data = audit([item(1, category="concise", details=details, estimated_reduction=12)])
        payload = json.loads(
            mod.render(data).split("const DATA = ")[1].split(";\nconst state")[0].replace("<\\/", "</")
        )
        self.assertEqual([d["label"] for d in payload["items"][0]["details"]], ["現状", "短縮案", "削減見込み"])
        self.assertEqual(payload["items"][0]["estimated_reduction"], 12)

    def test_reduction_total_skips_null(self):
        # フッタ合計はNumber()で0に落ちる。nullが合計を壊さないことをデータ側で保証する
        data = audit([
            item(1, category="concise", estimated_reduction=10),
            item(2, category="concise", estimated_reduction=None),
        ])
        payload = json.loads(
            mod.render(data).split("const DATA = ")[1].split(";\nconst state")[0].replace("<\\/", "</")
        )
        total = sum(int(i["estimated_reduction"] or 0) for i in payload["items"])
        self.assertEqual(total, 10)


class ContextExtractionTest(unittest.TestCase):
    def test_quote_present_marks_target_line(self):
        content = "\n".join(f"line {n}" for n in range(1, 21))
        context = mod.extract_context(content, "line 10")
        self.assertNotIn("error", context)
        targets = [line["number"] for line in context["lines"] if line["target"]]
        self.assertEqual(targets, [10])
        self.assertEqual(context["lines"][0]["number"], 7)
        self.assertEqual(context["lines"][-1]["number"], 13)

    def test_multiline_quote_marks_the_whole_span(self):
        content = "\n".join(f"line {n}" for n in range(1, 21))
        context = mod.extract_context(content, "line 10\nline 11")
        targets = [line["number"] for line in context["lines"] if line["target"]]
        self.assertEqual(targets, [10, 11])

    def test_quote_absent_reports_error_without_raising(self):
        context = mod.extract_context("alpha\nbravo", "存在しない引用")
        self.assertIn("見つかりません", context["error"])

    def test_empty_quote_reports_error(self):
        self.assertIn("error", mod.extract_context("alpha", ""))

    def test_missing_file_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("error", mod.read_config_file(Path(tmp) / "absent.md"))

    def test_binary_file_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "binary.bin"
            target.write_bytes(b"alpha\0bravo")
            self.assertIn("バイナリ", mod.read_config_file(target)["error"])

    def test_non_utf8_file_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sjis.md"
            target.write_bytes("日本語".encode("shift_jis"))
            self.assertIn("UTF-8", mod.read_config_file(target)["error"])


class PathHandlingTest(unittest.TestCase):
    def test_home_relative_path_is_expanded_for_reading(self):
        resolved = mod.resolve_path("~/example.md")
        self.assertTrue(resolved.is_absolute())
        self.assertNotIn("~", str(resolved))

    def test_display_path_is_not_expanded_in_the_report(self):
        # 個人絶対パスをHTMLへ漏らさない: 表示は入力のまま
        data = audit([item(1, file="~/.claude/CLAUDE.md")])
        html = mod.render(mod.prepare_report_data(data))
        self.assertIn("~/.claude/CLAUDE.md", html)
        self.assertNotIn(str(Path.home()), html)


class PrepareReportDataTest(unittest.TestCase):
    def test_context_is_attached_per_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.md"
            target.write_text("alpha\nbravo\ncharlie\n", encoding="utf-8")
            data = audit([item(1, file=str(target), quote="bravo")])
            report = mod.prepare_report_data(data)
            self.assertIn("lines", report["items"][0]["code_context"])

    def test_source_audit_json_is_not_mutated(self):
        data = audit([item(1)])
        mod.prepare_report_data(data)
        self.assertNotIn("code_context", data["items"][0])


class MainTest(unittest.TestCase):
    def test_wrong_argument_count_returns_nonzero(self):
        self.assertEqual(mod.main(["generate_audit_report.py"]), 1)

    def test_writes_report_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.json"
            report_path = Path(tmp) / "report.html"
            audit_path.write_text(json.dumps(audit([item(1)])), encoding="utf-8")
            self.assertEqual(mod.main(["x", str(audit_path), str(report_path)]), 0)
            self.assertIn("設定監査レポート", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
