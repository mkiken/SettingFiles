import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "generate_review_report.py"

spec = importlib.util.spec_from_file_location("generate_review_report", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def merged(items):
    return {
        "schema_version": 1,
        "pr_number": 123,
        "head_ref_oid": "abc123",
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


class MainTest(unittest.TestCase):
    def test_main_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "merged.json"
            dst = Path(tmp) / "report.html"
            src.write_text(json.dumps(merged([item(1)])), encoding="utf-8")
            rc = mod.main(["prog", str(src), str(dst)])
            self.assertEqual(rc, 0)
            self.assertIn("サンプル指摘", dst.read_text(encoding="utf-8"))

    def test_main_usage_error(self):
        self.assertEqual(mod.main(["prog"]), 1)


if __name__ == "__main__":
    unittest.main()
