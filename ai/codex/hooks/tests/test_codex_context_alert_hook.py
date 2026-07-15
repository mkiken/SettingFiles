import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HOOK = REPO_ROOT / "ai" / "codex" / "hooks" / "codex-context-alert.sh"
CONTEXT_ALERT = REPO_ROOT / "shell" / "zsh" / "alias" / "context-alert.zsh"
MODEL_CONTEXT_WINDOW = 258400
CONTEXT_BASELINE = 12000


def write_jsonl(path: Path, events: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event) + "\n")


def context_tokens_for_used_pct(used_pct: int) -> int:
    effective_window = MODEL_CONTEXT_WINDOW - CONTEXT_BASELINE
    return CONTEXT_BASELINE + round(effective_window * used_pct / 100)


def token_count_event(used_pct: int) -> dict:
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {"total_tokens": 774025},
                "last_token_usage": {
                    "total_tokens": context_tokens_for_used_pct(used_pct)
                },
                "model_context_window": MODEL_CONTEXT_WINDOW,
            },
        },
    }


def install_test_alert_dependencies(tmp_path: Path) -> Path:
    set_root = tmp_path / "set"
    alias_dir = set_root / "shell" / "zsh" / "alias"
    tmux_dir = set_root / "shell" / "tmux"
    alias_dir.mkdir(parents=True)
    tmux_dir.mkdir(parents=True)
    (alias_dir / "context-alert.zsh").symlink_to(CONTEXT_ALERT)
    (alias_dir / "notification.zsh").write_text(
        """function notify() {
  [[ -n \"${NOTIFY_FORCE:-}\" ]] || return 0
  printf '%s\\n' \"$*\" >> \"${NOTIFY_LOG}\"
}
""",
        encoding="utf-8",
    )
    (tmux_dir / "tmux_notification_title.sh").write_text(
        """function build_notification_title() {
  printf '%s %s %s' \"$1\" \"$2\" \"$3\"
}
""",
        encoding="utf-8",
    )
    (tmux_dir / "tmux_emoji.conf").write_text(
        "EMOJI_ID_CODEX=🪷\n", encoding="utf-8"
    )
    (tmux_dir / "tmux_window_name.sh").write_text(
        """function add_tmux_context_alert_badge() {
  printf 'add\\n' >> \"${TMUX_LOG}\"
}
function remove_tmux_context_alert_badge() {
  printf 'remove\\n' >> \"${TMUX_LOG}\"
}
""",
        encoding="utf-8",
    )
    return set_root


def hook_environment(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "SET": str(install_test_alert_dependencies(tmp_path)) + "/",
            "TMPDIR": str(tmp_path),
            "TERM_PROGRAM": "",
            "TMUX_PANE": "",
            "DISABLE_NOTIFY": "1",
            "NOTIFY_LOG": str(tmp_path / "notify.log"),
            "TMUX_LOG": str(tmp_path / "tmux.log"),
        }
    )
    return env


def run_hook(
    transcript_path: Path,
    session_id: str,
    env: dict[str, str],
    hook_event_name: str = "PostToolUse",
) -> subprocess.CompletedProcess[str]:
    hook_input = {
        "hook_event_name": hook_event_name,
        "session_id": session_id,
        "transcript_path": str(transcript_path),
    }
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(hook_input),
        text=True,
        env=env,
        capture_output=True,
        check=False,
    )


class CodexContextAlertHookTest(unittest.TestCase):
    def test_threshold_boundaries_force_notification_and_update_tmux_badge(self):
        cases = (
            (69, 0, (), "remove"),
            (70, 70, ("残り30%",), "add"),
            (84, 70, ("残り30%",), "add"),
            (85, 85, ("残り30%", "残り15%"), "add"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            session_id = "threshold-boundaries"
            env = hook_environment(tmp_path)

            for used_pct, expected_stage, expected_notices, expected_tmux in cases:
                with self.subTest(used_pct=used_pct):
                    transcript_path = tmp_path / "sessions" / f"rollout-{session_id}.jsonl"
                    write_jsonl(transcript_path, [token_count_event(used_pct)])

                    result = run_hook(transcript_path, session_id, env)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    state = tmp_path / "ai-context-alert" / f"codex-{session_id}.state"
                    self.assertEqual(
                        state.read_text(encoding="utf-8").strip(),
                        f"{expected_stage} {used_pct}",
                    )
                    tmux_actions = (tmp_path / "tmux.log").read_text(
                        encoding="utf-8"
                    ).splitlines()
                    self.assertEqual(tmux_actions[-1], expected_tmux)
                    notify_log = tmp_path / "notify.log"
                    if not expected_notices:
                        self.assertFalse(notify_log.exists())
                    else:
                        notices = notify_log.read_text(encoding="utf-8").splitlines()
                        self.assertEqual(len(notices), len(expected_notices))
                        for notice, expected_notice in zip(notices, expected_notices):
                            self.assertIn(expected_notice, notice)

    def test_low_context_usage_clears_existing_alert_state(self):
        session_id = "test-session"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            transcript_path = tmp_path / "sessions" / f"rollout-{session_id}.jsonl"
            write_jsonl(transcript_path, [token_count_event(14)])
            state_dir = tmp_path / "ai-context-alert"
            state_dir.mkdir()
            state_path = state_dir / f"codex-{session_id}.state"
            state_path.write_text("70 78\n", encoding="utf-8")
            env = hook_environment(tmp_path)

            result = run_hook(transcript_path, session_id, env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(state_path.read_text(encoding="utf-8").strip(), "0 14")

    def test_stop_rechecks_after_final_token_count_is_written(self):
        session_id = "delayed-stop"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            transcript_path = tmp_path / "sessions" / f"rollout-{session_id}.jsonl"
            write_jsonl(transcript_path, [token_count_event(69)])
            env = hook_environment(tmp_path)
            env["CODEX_CONTEXT_ALERT_RECHECK_DELAY_SECONDS"] = "0.2"

            result = run_hook(transcript_path, session_id, env, hook_event_name="Stop")
            self.assertEqual(result.returncode, 0, result.stderr)
            write_jsonl(transcript_path, [token_count_event(70)])

            state_path = tmp_path / "ai-context-alert" / f"codex-{session_id}.state"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if state_path.exists() and state_path.read_text(encoding="utf-8").startswith("70 "):
                    break
                time.sleep(0.05)

            self.assertEqual(state_path.read_text(encoding="utf-8").strip(), "70 70")
            self.assertIn("残り30%", (tmp_path / "notify.log").read_text(encoding="utf-8"))
            self.assertEqual(
                (tmp_path / "tmux.log").read_text(encoding="utf-8").splitlines()[-1],
                "add",
            )


if __name__ == "__main__":
    unittest.main()
