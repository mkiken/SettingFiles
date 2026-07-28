import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "generate_review_report.py"

spec = importlib.util.spec_from_file_location("generate_review_report", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def merged(items):
    return {
        "schema_version": 2,
        "pr_number": 123,
        "head_ref_oid": "abc123",
        "head_ref_name": "feature/report-ui",
        "repository": {
            "name": "octo/example",
            "url": "https://github.com/octo/example",
        },
        "pr_url": "https://github.com/octo/example/pull/123",
        "pr_title": "レビュー画面を改善する",
        "pr_author": "octocat",
        "run_dir": "/tmp/run",
        "sources": ["claude", "codex"],
        "items": items,
    }


def item(id_, **overrides):
    base = {
        "id": id_,
        "file": "src/app.py",
        "line_spec": "42",
        "area": "バグ検出",
        "priority": "high",
        "summary": "サンプル指摘",
        "carryover": None,
        "sources": [
            {"ai": "claude", "original_number": 1, "priority": "high",
             "impact": "High", "confidence": 85, "text": "詳細説明"},
        ],
    }
    base.update(overrides)
    return base


class RenderTest(unittest.TestCase):
    def test_render_embeds_data_and_placeholder_removed(self):
        html = mod.render(merged([item(1)]))
        self.assertIn('"pr_number": 123'.replace(" ", ""),
                      html.replace(" ", ""))
        self.assertNotIn("__REVIEW_DATA__", html)

    def test_render_priorities_table_driven(self):
        cases = ["high", "medium", "low"]
        for prio in cases:
            with self.subTest(prio=prio):
                html = mod.render(merged([item(1, priority=prio)]))
                self.assertIn("サンプル指摘", html)

    def test_render_zero_items(self):
        html = mod.render(merged([]))
        self.assertIn("<html", html)
        self.assertNotIn("__REVIEW_DATA__", html)

    def test_script_close_tag_escaped(self):
        html = mod.render(merged([item(1, summary="悪意ある</script>タグ")]))
        # 埋め込みJSON内で </ が <\/ にエスケープされ、scriptが早期閉鎖されない
        self.assertNotIn("悪意ある</script>", html)
        self.assertIn("悪意ある<\\/script>", html)

    def test_multi_source_and_carryover(self):
        it = item(
            1,
            carryover="skipped_before",
            sources=[
                {"ai": "claude", "original_number": 1, "priority": "high",
                 "impact": "High", "confidence": 85, "text": "claude詳細"},
                {"ai": "codex", "original_number": 3, "priority": "medium",
                 "impact": "Medium", "confidence": 70, "text": "codex詳細"},
            ],
        )
        html = mod.render(merged([it]))
        self.assertIn("claude詳細", html)
        self.assertIn("codex詳細", html)
        self.assertIn("skipped_before", html)

    def test_render_contains_report_ui_features(self):
        html = mod.render(merged([item(1)]))
        self.assertIn("状態ファイルを保存", html)
        self.assertIn("最大信頼度", html)
        self.assertIn("ai-review-report-theme", html)
        self.assertIn("markdown-code", html)
        self.assertIn("aria-expanded", html)
        self.assertIn('input.type="checkbox"', html)
        self.assertNotIn('input.type="radio"', html)
        self.assertIn("🔧 対応する", html)
        self.assertIn("🚫 対応しない", html)
        self.assertIn("decision-adopt", html)
        self.assertIn("decision-skip", html)
        self.assertIn("#expand-all", html)
        self.assertIn("#save-state", html)
        self.assertIn(".card-toggle{color:var(--link)}", html)
        self.assertIn('data-filter="pending"', html)
        self.assertIn("対応するリスト", html)
        self.assertIn("対応しないリスト", html)
        self.assertNotIn("toggle-completed", html)

    def test_decision_controls_are_mutually_exclusive_and_clearable(self):
        html = mod.render(merged([item(1)]))
        self.assertIn('s.reviewed=input.checked&&value==="reviewed"', html)
        self.assertIn('s.adopt=input.checked&&value==="adopt"', html)
        self.assertIn('input.value==="adopt"?s.adopt:s.reviewed', html)
        self.assertIn("const counts={pending:DATA.items.length-done", html)

    def test_state_save_is_in_footer_and_requires_all_items_completed(self):
        html = mod.render(merged([item(1)]))
        markup = html.split("<script>", 1)[0]
        self.assertLess(markup.index('<div id="report"'), markup.index("<footer>"))
        self.assertLess(markup.index("<footer>"), markup.index('id="save-state"'))
        self.assertIn('<button id="save-state" disabled>', markup)
        self.assertIn(
            'document.getElementById("save-state").disabled='
            "!CAN_SAVE_STATE||done!==DATA.items.length",
            html,
        )
        self.assertIn("function allItemsCompleted()", html)
        self.assertIn('fetch("/api/state"', html)
        self.assertIn("window.confirm", html)
        self.assertIn("すべての指摘を判断しました。state.json に保存しますか？", html)
        self.assertIn("showSaveFilePicker", html)

    def test_filters_replace_completed_toggle(self):
        html = mod.render(merged([item(1)]))
        self.assertIn('let fileHandle = null, filterMode = "pending"', html)
        self.assertIn("function matchesFilter(s)", html)
        self.assertIn('c.hidden=!matchesFilter(s)', html)
        self.assertIn("group.hidden=![...group.querySelectorAll", html)
        self.assertNotIn("showCompleted", html)

    def test_copy_params_control_is_removed(self):
        html = mod.render(merged([item(1)]))
        self.assertNotIn("番号をコピー", html)
        self.assertNotIn("copy-params", html)
        self.assertNotIn("clipboard.writeText", html)

    def test_schema_v1_remains_renderable(self):
        legacy = merged([item(1)])
        legacy["schema_version"] = 1
        for key in ("head_ref_name", "repository", "pr_url", "pr_title", "pr_author"):
            legacy.pop(key, None)
        html = mod.render(legacy)
        self.assertIn("AI Review Report", html)
        self.assertIn('"schema_version": 1', html)


class ContextTest(unittest.TestCase):
    def test_parse_line_spec(self):
        self.assertEqual(mod.parse_line_spec("42"), (42, 42))
        self.assertEqual(mod.parse_line_spec("42-50"), (42, 50))
        self.assertEqual(mod.parse_line_spec("~42"), (42, 42))
        self.assertIsNone(mod.parse_line_spec("line 42"))

    def test_extract_context_marks_target_and_padding(self):
        content = "\n".join(f"line {number}" for number in range(1, 12))
        context = mod.extract_context(content, "5-6")
        self.assertEqual([line["number"] for line in context["lines"]], list(range(2, 10)))
        self.assertEqual([line["number"] for line in context["lines"] if line["target"]], [5, 6])

    def test_prepare_report_data_adds_links_and_context(self):
        source = merged([item(1, line_spec="4-5")])
        with patch.object(mod, "read_git_file", return_value=b"1\n2\n3\n4\n5\n6\n7\n8\n"):
            prepared = mod.prepare_report_data(source, Path("/repo"))
        report_item = prepared["items"][0]
        self.assertIn("/files#diff-", report_item["links"]["pr_diff"])
        self.assertTrue(report_item["links"]["pr_diff"].endswith("R4"))
        self.assertTrue(report_item["links"]["snapshot"].endswith("#L4-L5"))
        self.assertEqual([line["number"] for line in report_item["code_context"]["lines"]], list(range(1, 9)))

    def test_prepare_report_data_handles_unavailable_code(self):
        with patch.object(mod, "read_git_file", return_value=None), \
             patch.object(mod, "read_github_file", return_value=None):
            prepared = mod.prepare_report_data(merged([item(1)]), Path("/repo"))
        self.assertIn("取得できません", prepared["items"][0]["code_context"]["error"])


class MainTest(unittest.TestCase):
    def test_main_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "merged.json"
            dst = Path(tmp) / "report.html"
            src.write_text(json.dumps(merged([item(1)])), encoding="utf-8")
            with patch.object(mod, "prepare_report_data", side_effect=lambda data, _: data):
                rc = mod.main(["prog", str(src), str(dst)])
            self.assertEqual(rc, 0)
            self.assertIn("サンプル指摘", dst.read_text(encoding="utf-8"))

    def test_main_usage_error(self):
        self.assertEqual(mod.main(["prog"]), 1)


if __name__ == "__main__":
    unittest.main()
