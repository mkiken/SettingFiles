import importlib.util
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest import mock


from support import REPO_ROOT
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "serve_review_report.py"

spec = importlib.util.spec_from_file_location("serve_review_report", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReviewServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        (self.run_dir / "merged.json").write_text(
            json.dumps({"items": [{"id": 1}, {"id": 2}]}), encoding="utf-8"
        )
        (self.run_dir / "report.html").write_text("<h1>report</h1>", encoding="utf-8")
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
        request = Request(self.server.url.removesuffix("/report.html") + path, body, headers, method=method)
        return urlopen(request, timeout=2)

    def valid_state(self):
        return {
            "schema_version": 2,
            "items": {
                "1": {"decision": "fix"},
                "2": {"decision": "post"},
            },
        }

    def test_serves_only_report(self):
        with self.request("/report.html") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"<h1>report</h1>")
        with self.assertRaises(HTTPError) as error:
            self.request("/merged.json")
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_valid_state_is_saved_atomically(self):
        body = json.dumps(self.valid_state()).encode()
        with self.request("/api/state", "POST", body, "application/json") as response:
            self.assertEqual(response.status, 204)
        state_path = self.run_dir / "state.json"
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), self.valid_state())
        self.assertEqual(list(self.run_dir.glob(".state.json.*.tmp")), [])

    def test_invalid_state_is_rejected_without_writing(self):
        invalid = self.valid_state()
        invalid["items"]["1"] = {"decision": "both"}
        with self.assertRaises(HTTPError) as error:
            self.request("/api/state", "POST", json.dumps(invalid).encode(), "application/json")
        self.assertEqual(error.exception.code, 400)
        error.exception.close()
        self.assertFalse((self.run_dir / "state.json").exists())

    def test_schema_version_1_payload_is_rejected(self):
        legacy = {
            "schema_version": 1,
            "items": {
                "1": {"reviewed": False, "adopt": True},
                "2": {"reviewed": True, "adopt": False},
            },
        }
        with self.assertRaises(HTTPError) as error:
            self.request("/api/state", "POST", json.dumps(legacy).encode(), "application/json")
        self.assertEqual(error.exception.code, 400)
        error.exception.close()
        self.assertFalse((self.run_dir / "state.json").exists())

    def test_null_decision_is_accepted(self):
        partial = self.valid_state()
        partial["items"]["2"] = {"decision": None}
        body = json.dumps(partial).encode()
        with self.request("/api/state", "POST", body, "application/json") as response:
            self.assertEqual(response.status, 204)
        self.assertEqual(
            json.loads((self.run_dir / "state.json").read_text(encoding="utf-8")), partial
        )

    def test_missing_item_key_is_rejected(self):
        incomplete = self.valid_state()
        del incomplete["items"]["2"]
        with self.assertRaises(HTTPError) as error:
            self.request("/api/state", "POST", json.dumps(incomplete).encode(), "application/json")
        self.assertEqual(error.exception.code, 400)
        error.exception.close()
        self.assertFalse((self.run_dir / "state.json").exists())

    def test_unknown_item_and_non_json_requests_are_rejected(self):
        invalid = self.valid_state()
        invalid["items"]["3"] = invalid["items"].pop("2")
        with self.assertRaises(HTTPError) as unknown_error:
            self.request("/api/state", "POST", json.dumps(invalid).encode(), "application/json")
        self.assertEqual(unknown_error.exception.code, 400)
        unknown_error.exception.close()
        with self.assertRaises(HTTPError) as type_error:
            self.request("/api/state", "POST", b"{}", "text/plain")
        self.assertEqual(type_error.exception.code, 415)
        type_error.exception.close()
        self.assertFalse((self.run_dir / "state.json").exists())

    def test_heartbeat_is_accepted(self):
        with self.request("/api/heartbeat", "POST", b"") as response:
            self.assertEqual(response.status, 204)

    def test_api_info_returns_run_dir(self):
        with self.request("/api/info") as response:
            self.assertEqual(response.status, 200)
            body = json.loads(response.read())
        self.assertEqual(body["run_dir"], str(self.run_dir.resolve()))


class ServerInfoFileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        (self.run_dir / "merged.json").write_text(
            json.dumps({"items": [{"id": 1}]}), encoding="utf-8"
        )
        (self.run_dir / "report.html").write_text("<h1>report</h1>", encoding="utf-8")

    def start_server(self):
        server = mod.ReviewServer(self.run_dir, idle_timeout=60)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.addCleanup(stop)
        return server

    def test_write_server_info_creates_file_with_url_port_pid(self):
        server = self.start_server()
        server.write_server_info()
        info = json.loads((self.run_dir / ".server.json").read_text(encoding="utf-8"))
        self.assertEqual(info["url"], server.url)
        self.assertEqual(info["port"], server.server_port)
        self.assertEqual(info["pid"], mod.os.getpid())

    def test_remove_server_info_deletes_own_pid_file(self):
        server = self.start_server()
        server.write_server_info()
        server.remove_server_info()
        self.assertFalse((self.run_dir / ".server.json").exists())

    def test_remove_server_info_preserves_other_pid_file(self):
        server = self.start_server()
        server_info_path = self.run_dir / ".server.json"
        mod.write_json_atomically(
            server_info_path, {"schema_version": 1, "url": "http://x", "port": 1, "pid": 999999}
        )
        server.remove_server_info()
        self.assertTrue(server_info_path.exists())
        info = json.loads(server_info_path.read_text(encoding="utf-8"))
        self.assertEqual(info["pid"], 999999)

    def test_probe_reusable_server_returns_url_when_run_dir_matches(self):
        server = self.start_server()
        server.write_server_info()
        url = mod.probe_reusable_server(self.run_dir / ".server.json", self.run_dir.resolve())
        self.assertEqual(url, server.url)

    def test_probe_reusable_server_none_when_run_dir_mismatches(self):
        server = self.start_server()
        server.write_server_info()
        other_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, other_dir, ignore_errors=True)
        url = mod.probe_reusable_server(self.run_dir / ".server.json", other_dir)
        self.assertIsNone(url)

    def test_probe_reusable_server_none_when_stale(self):
        server_info_path = self.run_dir / ".server.json"
        # 生存確認できない閉じたポートを指すstaleな.server.json
        mod.write_json_atomically(
            server_info_path, {"schema_version": 1, "url": "http://127.0.0.1:1/report.html", "port": 1, "pid": 999999}
        )
        url = mod.probe_reusable_server(server_info_path, self.run_dir.resolve())
        self.assertIsNone(url)

    def test_probe_reusable_server_none_when_missing(self):
        url = mod.probe_reusable_server(self.run_dir / ".server.json", self.run_dir.resolve())
        self.assertIsNone(url)

    def test_serve_reuses_existing_server_without_starting_new_one(self):
        server = self.start_server()
        server.write_server_info()
        with mock.patch.object(mod, "ReviewServer") as review_server_cls:
            mod.serve(self.run_dir, idle_timeout=60, open_browser=False)
        review_server_cls.assert_not_called()

    def test_main_default_idle_timeout_is_43200(self):
        with mock.patch.object(mod, "serve") as serve_mock:
            mod.main([str(self.run_dir)])
        self.assertEqual(serve_mock.call_args.args[1], 43200)
