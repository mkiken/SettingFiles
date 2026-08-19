#!/usr/bin/env python3
"""Serve one AI review report and persist its state on the loopback interface."""

import argparse
import json
import os
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MAX_STATE_BYTES = 1024 * 1024
PROBE_TIMEOUT = 0.5


def expected_item_ids(run_dir):
    with (run_dir / "merged.json").open(encoding="utf-8") as source:
        merged = json.load(source)
    return {str(item["id"]) for item in merged.get("items", [])}


DECISIONS = frozenset({"fix", "post", "dismiss", None})


def validate_state(payload, item_ids):
    if not isinstance(payload, dict) or payload.get("schema_version") != 2:
        raise ValueError("schema_version must be 2")
    items = payload.get("items")
    if not isinstance(items, dict) or set(items) != item_ids:
        raise ValueError("state items do not match this report")
    for item_id, entry in items.items():
        if not isinstance(item_id, str) or not isinstance(entry, dict):
            raise ValueError("invalid state item")
        decision = entry.get("decision")
        # None は「未判断」。保存ボタンはHTML側で全項目確定まで非活性なので通常は届かないが、
        # 部分保存自体はサーバー側で拒否しない。
        if decision not in DECISIONS:
            raise ValueError("decision must be one of fix / post / dismiss / null")


def write_json_atomically(path, payload):
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=1)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_state(path, payload):
    write_json_atomically(path, payload)


def read_server_info(server_info_path):
    try:
        return json.loads(server_info_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def probe_reusable_server(server_info_path, run_dir):
    """既存.server.jsonが同じrun_dirを指す生存サーバーなら、そのURLを返す。"""
    info = read_server_info(server_info_path)
    if not isinstance(info, dict):
        return None
    port = info.get("port")
    url = info.get("url")
    if not isinstance(port, int) or not isinstance(url, str):
        return None
    try:
        with urlopen(
            Request(f"http://127.0.0.1:{port}/api/info"), timeout=PROBE_TIMEOUT
        ) as response:
            remote = json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, ValueError, TimeoutError):
        return None
    # ポート番号はOSに再利用されうるため、run_dir一致をもって初めて同一サーバーとみなす。
    # heartbeatの200/204応答だけでは別プロセスへの誤接続を排除できない。
    if remote.get("run_dir") != str(run_dir):
        return None
    return url


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, run_dir, idle_timeout):
        self.run_dir = Path(run_dir).resolve()
        self.report_path = self.run_dir / "report.html"
        self.state_path = self.run_dir / "state.json"
        self.server_info_path = self.run_dir / ".server.json"
        self.item_ids = expected_item_ids(self.run_dir)
        self.idle_timeout = idle_timeout
        self.last_activity = time.monotonic()
        super().__init__(("127.0.0.1", 0), ReviewHandler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}/report.html"

    def touch(self):
        self.last_activity = time.monotonic()

    def write_server_info(self):
        write_json_atomically(
            self.server_info_path,
            {"schema_version": 1, "url": self.url, "port": self.server_port, "pid": os.getpid()},
        )

    def remove_server_info(self):
        # 自分が書いたものだけ消す: 別プロセスが上書き済みなら他プロセスの情報を破壊しない
        info = read_server_info(self.server_info_path)
        if isinstance(info, dict) and info.get("pid") == os.getpid():
            try:
                self.server_info_path.unlink()
            except FileNotFoundError:
                pass


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, format, *args):
        return

    def send_text(self, status, text="", content_type="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/info":
            # 再利用検出用のprobeなので、生存確認だけでlast_activityは更新しない
            # （probeだけでアイドル判定を遅らせて孤児サーバーを不必要に延命させない）
            self.send_text(
                HTTPStatus.OK, json.dumps({"run_dir": str(self.server.run_dir)}), "application/json"
            )
            return
        self.server.touch()
        if path not in ("/", "/report.html"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            report = self.server.report_path.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(report)))
        self.end_headers()
        self.wfile.write(report)

    def do_POST(self):
        path = urlparse(self.path).path
        self.server.touch()
        if path == "/api/heartbeat":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if path != "/api/state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if self.headers.get_content_type() != "application/json":
            self.send_text(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "application/json is required")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_STATE_BYTES:
            self.send_text(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "invalid state size")
            return
        try:
            payload = json.loads(self.rfile.read(length))
            validate_state(payload, self.server.item_ids)
            write_state(self.server.state_path, payload)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self.send_text(HTTPStatus.BAD_REQUEST, str(error))
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()


def stop_after_idle(server):
    while True:
        time.sleep(1)
        if time.monotonic() - server.last_activity > server.idle_timeout:
            server.shutdown()
            return


def serve(run_dir, idle_timeout=43200, open_browser=False):
    run_dir = Path(run_dir).resolve()
    reusable_url = probe_reusable_server(run_dir / ".server.json", run_dir)
    if reusable_url is not None:
        if open_browser:
            subprocess.run(["open", "-a", "Google Chrome", reusable_url], check=False)
        print(reusable_url, flush=True)
        return

    server = ReviewServer(run_dir, idle_timeout)
    server.write_server_info()
    watchdog = threading.Thread(target=stop_after_idle, args=(server,), daemon=True)
    watchdog.start()
    if open_browser:
        subprocess.run(["open", "-a", "Google Chrome", server.url], check=False)
    print(server.url, flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.remove_server_info()
        server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--idle-timeout", type=int, default=43200)
    args = parser.parse_args(argv)
    if args.idle_timeout <= 0:
        parser.error("--idle-timeout must be positive")
    if not (args.run_dir / "merged.json").is_file() or not (args.run_dir / "report.html").is_file():
        parser.error("run_dir must contain merged.json and report.html")
    serve(args.run_dir, args.idle_timeout, args.open_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
