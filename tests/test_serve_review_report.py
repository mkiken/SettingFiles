import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
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
            "schema_version": 1,
            "items": {
                "1": {"reviewed": False, "adopt": True},
                "2": {"reviewed": True, "adopt": False},
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
        invalid["items"]["1"] = {"reviewed": True, "adopt": True}
        with self.assertRaises(HTTPError) as error:
            self.request("/api/state", "POST", json.dumps(invalid).encode(), "application/json")
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
