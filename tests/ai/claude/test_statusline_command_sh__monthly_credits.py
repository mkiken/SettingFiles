import json
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


class StatuslineMonthlyCreditsTest(unittest.TestCase):
    def run_statusline(self, claude_json_content: dict | None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            if claude_json_content is not None:
                (home / ".claude.json").write_text(
                    json.dumps(claude_json_content), encoding="utf-8"
                )
            env = sanitized_env(
                {"HOME": str(home), "SET": str(home / "missing-settingfiles")}
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


if __name__ == "__main__":
    unittest.main()
