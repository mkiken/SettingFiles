import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "serve_review_report.py"

spec = importlib.util.spec_from_file_location("serve_review_report_audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ProfileDetectionTest(unittest.TestCase):
    def make_run_dir(self, manifest_name):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        run_dir = Path(temp.name)
        if manifest_name:
            (run_dir / manifest_name).write_text(
                json.dumps({"items": [{"id": 1}]}), encoding="utf-8"
            )
        (run_dir / "report.html").write_text("<h1>report</h1>", encoding="utf-8")
        return run_dir

    def test_merged_json_detects_review(self):
        self.assertEqual(mod.detect_profile(self.make_run_dir("merged.json")), "review")

    def test_audit_json_detects_audit(self):
        self.assertEqual(mod.detect_profile(self.make_run_dir("audit.json")), "audit")

    def test_neither_manifest_detects_nothing(self):
        self.assertIsNone(mod.detect_profile(self.make_run_dir(None)))

    def test_server_rejects_run_dir_without_a_manifest(self):
        with self.assertRaises(ValueError):
            mod.ReviewServer(self.make_run_dir(None), idle_timeout=60)


class ValidateStateProfileTest(unittest.TestCase):
    def state(self, decision, schema_version):
        return {"schema_version": schema_version, "items": {"1": {"decision": decision}}}

    def test_audit_accepts_apply_and_dismiss(self):
        for decision in ("apply", "dismiss", None):
            with self.subTest(decision=decision):
                mod.validate_state(self.state(decision, 1), {"1"}, "audit")

    def test_audit_rejects_review_decisions(self):
        # プロファイルが実際に分離されていることの証明: fix は監査側では無効
        for decision in ("fix", "post"):
            with self.subTest(decision=decision):
                with self.assertRaises(ValueError):
                    mod.validate_state(self.state(decision, 1), {"1"}, "audit")

    def test_review_rejects_audit_decision(self):
        with self.assertRaises(ValueError):
            mod.validate_state(self.state("apply", 2), {"1"}, "review")

    def test_audit_rejects_review_schema_version(self):
        with self.assertRaises(ValueError):
            mod.validate_state(self.state("apply", 2), {"1"}, "audit")

    def test_review_rejects_audit_schema_version(self):
        with self.assertRaises(ValueError):
            mod.validate_state(self.state("fix", 1), {"1"}, "review")

    def test_item_id_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate_state(self.state("apply", 1), {"1", "2"}, "audit")


class AuditServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        (self.run_dir / "audit.json").write_text(
            json.dumps({"schema_version": 1, "items": [{"id": 1}, {"id": 2}]}), encoding="utf-8"
        )
        (self.run_dir / "report.html").write_text("<h1>audit report</h1>", encoding="utf-8")
        self.server = mod.ReviewServer(self.run_dir, idle_timeout=60)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET", body=None, content_type=None):
        headers = {"Content-Type": content_type} if content_type else {}
        base = self.server.url.removesuffix("/report.html")
        return urlopen(Request(base + path, body, headers, method=method), timeout=2)

    def post_state(self, payload):
        return self.request(
            "/api/state",
            method="POST",
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    def test_profile_is_audit(self):
        self.assertEqual(self.server.profile_name, "audit")

    def test_serves_report_html(self):
        self.assertIn("audit report", self.request("/report.html").read().decode("utf-8"))

    def test_api_info_reports_run_dir(self):
        # サーバーは run_dir を resolve() する。macOSの /var -> /private/var を吸収して比較する
        payload = json.loads(self.request("/api/info").read().decode("utf-8"))
        self.assertEqual(payload["run_dir"], str(self.run_dir.resolve()))

    def test_accepts_audit_state_and_writes_it(self):
        payload = {
            "schema_version": 1,
            "items": {"1": {"decision": "apply"}, "2": {"decision": "dismiss"}},
        }
        self.assertEqual(self.post_state(payload).status, 204)
        written = json.loads((self.run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(written, payload)

    def test_rejects_review_decision(self):
        payload = {"schema_version": 1, "items": {"1": {"decision": "fix"}, "2": {"decision": "dismiss"}}}
        with self.assertRaises(HTTPError) as caught:
            self.post_state(payload)
        self.assertEqual(caught.exception.code, 400)

    def test_rejects_mismatched_item_ids(self):
        payload = {"schema_version": 1, "items": {"1": {"decision": "apply"}}}
        with self.assertRaises(HTTPError) as caught:
            self.post_state(payload)
        self.assertEqual(caught.exception.code, 400)


class MainArgumentTest(unittest.TestCase):
    def test_main_errors_without_any_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "report.html").write_text("<h1>x</h1>", encoding="utf-8")
            with self.assertRaises(SystemExit):
                mod.main([str(run_dir)])

    def test_main_errors_when_report_html_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "audit.json").write_text(json.dumps({"items": []}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                mod.main([str(run_dir)])


if __name__ == "__main__":
    unittest.main()
