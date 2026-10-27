import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

STATUSLINE = REPO_ROOT / "ai/claude/statusline-command.sh"


def extra_usage(**overrides) -> dict:
    base = {
        "is_enabled": True,
        "monthly_limit": 80000,
        "used_credits": 57355,
        "utilization": 71.69375,
        "currency": "USD",
        "decimal_places": 2,
    }
    base.update(overrides)
    return base


def claude_json(extra: dict | None, *, age_sec: int = 60) -> dict:
    if extra is None:
        return {}
    return {
        "cachedUsageUtilization": {
            "fetchedAtMs": int((time.time() - age_sec) * 1000),
            "utilization": {"extra_usage": extra},
        }
    }


def usage_cache(extra: dict, *, age_sec: int = 10) -> dict:
    """独自キャッシュは cachedUsageUtilization の中身と同形。"""
    return claude_json(extra, age_sec=age_sec)["cachedUsageUtilization"]


FRESH_EXTRA = extra_usage(used_credits=66119, utilization=82.65)


class StatuslineMonthlyCreditsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.cache_dir = self.home / "xdg" / "claude-statusline"
        self.cache_dir.mkdir(parents=True)
        self.security_trace = self.home / "security.trace"
        self.curl_trace = self.home / "curl.trace"
        self.stub_security("")
        self.stub_curl(json.dumps({"extra_usage": FRESH_EXTRA}))

    def stub_security(self, token: str):
        credentials = json.dumps({"claudeAiOauth": {"accessToken": token}}) if token else ""
        self.write_stub(
            "security",
            f"echo called >> '{self.security_trace}'\n"
            + (f"echo '{credentials}'\n" if token else "exit 44\n"),
        )

    def stub_curl(self, body: str | None):
        self.write_stub(
            "curl",
            f"echo called >> '{self.curl_trace}'\n"
            + (f"echo '{body}'\n" if body is not None else "exit 22\n"),
        )

    def write_stub(self, name: str, body: str):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
        path.chmod(0o755)

    def lock(self, *, age_sec: int = 0):
        lock = self.cache_dir / "lock"
        lock.mkdir()
        if age_sec:
            past = time.time() - age_sec
            os.utime(lock, (past, past))

    def wait_for(self, path: Path, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return True
            time.sleep(0.05)
        return False

    def settle(self):
        """デタッチされた取得処理が走り切るのを待つ(否定アサーション用)。"""
        time.sleep(0.5)

    def run_statusline(
        self,
        claude_json_content: dict | None,
        *,
        cache: dict | None = None,
        fetch: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """fetch=False は新しいロックを置き、裏の取得を抑止して表示だけを検証する。"""
        if claude_json_content is not None:
            (self.home / ".claude.json").write_text(
                json.dumps(claude_json_content), encoding="utf-8"
            )
        if cache is not None:
            (self.cache_dir / "usage.json").write_text(json.dumps(cache), encoding="utf-8")
        if not fetch and not (self.cache_dir / "lock").exists():
            self.lock()
        env = sanitized_env(
            {
                "HOME": str(self.home),
                "XDG_CACHE_HOME": str(self.home / "xdg"),
                "PATH": f"{self.bin}:{os.environ['PATH']}",
                "SET": str(self.home / "missing-settingfiles"),
            }
        )
        return subprocess.run(
            ["/bin/bash", str(STATUSLINE)],
            cwd=REPO_ROOT,
            env=env,
            input=json.dumps({"model": {"display_name": "Claude"}}),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_shows_used_over_limit_with_percent(self):
        result = self.run_statusline(claude_json(extra_usage()))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("💳 $574/$800 (72%)", result.stdout)
        self.assertNotIn("h前", result.stdout)

    def test_hidden_when_extra_usage_disabled(self):
        result = self.run_statusline(claude_json(extra_usage(is_enabled=False)))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("💳", result.stdout)

    def test_hidden_when_claude_json_missing(self):
        result = self.run_statusline(None)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("💳", result.stdout)
        self.assertIn("🤖 Claude", result.stdout)

    def test_hidden_when_cache_absent(self):
        result = self.run_statusline({"other": 1})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("💳", result.stdout)

    def test_hidden_when_fields_null(self):
        result = self.run_statusline(claude_json(extra_usage(monthly_limit=None)))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("💳", result.stdout)

    def test_stale_cache_shows_elapsed_hours(self):
        result = self.run_statusline(claude_json(extra_usage(), age_sec=2 * 3600 + 60))

        self.assertIn("💳 $574/$800 (72%)", result.stdout)
        self.assertIn("·2h前", result.stdout)

    def test_non_usd_currency_uses_code(self):
        result = self.run_statusline(
            claude_json(extra_usage(currency="JPY", decimal_places=0, used_credits=574, monthly_limit=800, utilization=71.75))
        )

        self.assertIn("💳 JPY 574/JPY 800 (72%)", result.stdout)

    def test_high_utilization_is_red(self):
        result = self.run_statusline(claude_json(extra_usage(used_credits=76000, utilization=95)))

        self.assertIn("\033[31m💳 $760/$800 (95%)", result.stdout)

    def test_prefers_own_cache_when_newer_than_claude_json(self):
        result = self.run_statusline(
            claude_json(extra_usage(), age_sec=8 * 3600),
            cache=usage_cache(FRESH_EXTRA),
        )

        self.assertIn("💳 $661/$800 (83%)", result.stdout)
        self.assertNotIn("h前", result.stdout)

    def test_prefers_claude_json_when_newer_than_own_cache(self):
        result = self.run_statusline(
            claude_json(extra_usage(), age_sec=30),
            cache=usage_cache(FRESH_EXTRA, age_sec=3600),
        )

        self.assertIn("💳 $574/$800 (72%)", result.stdout)

    def test_fresh_own_cache_does_not_fetch(self):
        self.stub_security("tok")

        self.run_statusline(None, cache=usage_cache(FRESH_EXTRA), fetch=True)
        self.settle()

        self.assertFalse(self.security_trace.exists())
        self.assertFalse(self.curl_trace.exists())

    def test_missing_cache_fetches_in_background_and_shows_next_render(self):
        self.stub_security("tok")

        first = self.run_statusline(claude_json(extra_usage(), age_sec=8 * 3600), fetch=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("💳 $574/$800 (72%)", first.stdout)
        self.assertTrue(self.wait_for(self.cache_dir / "usage.json"))

        second = self.run_statusline(None, fetch=True)
        self.assertIn("💳 $661/$800 (83%)", second.stdout)
        self.assertEqual(self.curl_trace.read_text().count("called"), 1)

    def test_failed_fetch_keeps_existing_cache_and_backs_off(self):
        self.stub_security("tok")
        self.stub_curl(None)
        stale = usage_cache(FRESH_EXTRA, age_sec=3600)
        cache_path = self.cache_dir / "usage.json"
        cache_path.write_text(json.dumps(stale), encoding="utf-8")

        self.run_statusline(None, fetch=True)
        self.assertTrue(self.wait_for(self.curl_trace))
        self.settle()

        self.assertEqual(json.loads(cache_path.read_text()), stale)
        self.assertEqual(sorted(p.name for p in self.cache_dir.iterdir()), ["lock", "usage.json"])

        # ロックが残っている間は再試行しない
        self.run_statusline(None, fetch=True)
        self.settle()
        self.assertEqual(self.curl_trace.read_text().count("called"), 1)

    def test_response_without_extra_usage_is_not_cached(self):
        self.stub_security("tok")
        self.stub_curl(json.dumps({"five_hour": None}))

        self.run_statusline(None, fetch=True)
        self.assertTrue(self.wait_for(self.curl_trace))
        self.settle()

        self.assertFalse((self.cache_dir / "usage.json").exists())

    def test_no_token_skips_curl(self):
        self.stub_security("")

        self.run_statusline(None, fetch=True)
        self.assertTrue(self.wait_for(self.security_trace))
        self.settle()

        self.assertFalse(self.curl_trace.exists())

    def test_fresh_lock_prevents_concurrent_fetch(self):
        self.stub_security("tok")
        self.lock()

        self.run_statusline(None, fetch=True)
        self.settle()

        self.assertFalse(self.security_trace.exists())
        self.assertFalse(self.curl_trace.exists())

    def test_expired_lock_is_reclaimed(self):
        self.stub_security("tok")
        self.lock(age_sec=300)

        self.run_statusline(None, fetch=True)

        self.assertTrue(self.wait_for(self.cache_dir / "usage.json"))


if __name__ == "__main__":
    unittest.main()
