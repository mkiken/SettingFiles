"""shell/zsh/notification.zsh の画面停止監視（⏸️）テスト。

実herdrには触れず、PATH先頭のfake herdrが `pane read`（画面）と `pane get`
（agent/focused）を返す。notify / アイコン更新はzshスタブで呼び出しを記録する。
閾値・間隔は環境変数で短縮する（HERDR_IDLE_WATCH_SECONDS / _INTERVAL）。
"""
import os
import signal
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

PANE_KEY = "w1_p1"

FAKE_HERDR = """#!/bin/sh
echo "$*" >> "$FAKE/herdr_calls"
case "$1 $2" in
  "pane read")
    [ -f "$FAKE/read_fail" ] && exit 1
    cat "$FAKE/screen"
    ;;
  "pane get")
    agent=null
    [ -s "$FAKE/agent" ] && agent="\\"$(cat "$FAKE/agent")\\""
    printf '{"result":{"pane":{"agent":%s,"focused":%s}}}\\n' "$agent" "$(cat "$FAKE/focused")"
    ;;
esac
exit 0
"""

TRAP_HERDR = """#!/bin/sh
echo "trap invoked: $*" >> "$FAKE/trap_log"
exit 0
"""

STUBS = r"""
EMOJI_STATUS_IDLE=⏸️
EMOJI_STATUS_NOTIFICATION=✋
EXIT_CODE_SIGINT=130
EXIT_CODE_SIGPIPE=141
add-zsh-hook() { :; }
notify() { print -r -- "notify:$*" >> "$CALL_LOG"; }
update_herdr_status_icon() { print -r -- "update:$*" >> "$CALL_LOG"; }
remove_herdr_idle_status_icon() { print -r -- "remove_idle" >> "$CALL_LOG"; }
remove_herdr_status_icon() { print -r -- "remove_herdr" >> "$CALL_LOG"; }
remove_tmux_window_icon() { :; }
_herdr_resolve_tab_id() { print -r -- "w1:t1"; }
_herdr_shell_status_marker_read() { [[ -f "$FAKE/marker" ]] && command cat "$FAKE/marker"; return 0; }

pidfile="$XDG_CACHE_HOME/herdr-idle-watch/w1_p1"
count_lines() {
  [[ -f "$CALL_LOG" ]] || { print 0; return 0; }
  command grep -c -F -- "$1" "$CALL_LOG" || true
}
wait_for_count() {
  local i
  for i in {1..150}; do
    (( $(count_lines "$1") >= $2 )) && return 0
    sleep 0.1
  done
  print -r -- "TIMEOUT:$1>=$2"
  return 1
}
alive() { kill -0 "$1" 2>/dev/null && print alive || print dead; }
"""


def parse_kv(stdout: str) -> dict[str, str]:
    result = {}
    for line in stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            result[key] = value
    return result


class HerdrIdleWatchTestBase(unittest.TestCase):
    def run_script(
        self,
        body: str,
        *,
        env: dict[str, str | None] | None = None,
        files: dict[str, str] | None = None,
        trap_herdr_bin: bool = False,
    ) -> tuple[dict[str, str], list[str], bool]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake = root / "fake"
            fake.mkdir()
            call_log = root / "calls"
            cache = root / "cache"

            herdr = fake_bin / "herdr"
            herdr.write_text(FAKE_HERDR, encoding="utf-8")
            herdr.chmod(herdr.stat().st_mode | stat.S_IXUSR)
            trap = root / "outside_path" / "herdr"
            trap.parent.mkdir()
            trap.write_text(TRAP_HERDR, encoding="utf-8")
            trap.chmod(trap.stat().st_mode | stat.S_IXUSR)

            initial = {"screen": "hello\n", "focused": "false", "agent": ""}
            initial.update(files or {})
            for name, content in initial.items():
                (fake / name).write_text(content, encoding="utf-8")

            overrides: dict[str, str | None] = {
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "HOME": "/nonexistent",
                "XDG_CACHE_HOME": str(cache),
                "CALL_LOG": str(call_log),
                "FAKE": str(fake),
                "SET": f"{REPO_ROOT}/",
                "HERDR_PANE_ID": "w1:p1",
                "HERDR_IDLE_WATCH_SECONDS": "1",
                "HERDR_IDLE_WATCH_INTERVAL": "0.2",
                # 実行元の環境が無効化していても結果が変わらないよう毎回外す
                "DISABLE_NOTIFY": None,
                "NOTIFY_SILENT": None,
                "_DISABLE_NOTIFY_FOR_CURRENT_CMD": None,
                "HERDR_BIN_PATH": None,
            }
            if trap_herdr_bin:
                overrides["HERDR_BIN_PATH"] = str(trap)
            overrides.update(env or {})
            run_env = sanitized_env({k: v for k, v in overrides.items() if v is not None})
            for key, value in overrides.items():
                if value is None:
                    run_env.pop(key, None)

            script = f"{STUBS}source shell/zsh/notification.zsh\n{body}\n"
            try:
                result = subprocess.run(
                    ["zsh", "-fc", script],
                    cwd=REPO_ROOT,
                    env=run_env,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
            finally:
                self.kill_leftover_watcher(cache)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines() if call_log.exists() else []
            trapped = (fake / "trap_log").exists()
            return parse_kv(result.stdout), calls, trapped

    @staticmethod
    def kill_leftover_watcher(cache: Path) -> None:
        pidfile = cache / "herdr-idle-watch" / PANE_KEY
        try:
            os.kill(int(pidfile.read_text().split()[0]), signal.SIGTERM)
        except (OSError, ValueError, IndexError):
            pass


class HerdrIdleWatchNotifyTest(HerdrIdleWatchTestBase):
    def test_unchanged_screen_notifies_once_and_precmd_cleans_up(self):
        out, calls, trapped = self.run_script(
            "_notification_preexec 'make build'\n"
            'pid="$_herdr_idle_watch_pid"\n'
            "wait_for_count 'notify:--tmux-icon ⏸️' 1 || exit 1\n"
            # 同じ停止の間は再通知しないことを確認するため、閾値を超えた後も待つ
            "sleep 1.5\n"
            'print -r -- "notify_count=$(count_lines notify:)"\n'
            'print -r -- "shown_flag=$([[ -f $pidfile.shown ]] && echo yes || echo no)"\n'
            "_notification_precmd\n"
            "sleep 0.3\n"
            'print -r -- "remove_idle=$(count_lines remove_idle)"\n'
            'print -r -- "watcher=$(alive $pid)"\n'
            'print -r -- "pidfile=$([[ -f $pidfile ]] && echo yes || echo no)"\n'
            'print -r -- "flag_after=$([[ -f $pidfile.shown ]] && echo yes || echo no)"\n',
            trap_herdr_bin=True,
        )
        self.assertEqual(out["notify_count"], "1", calls)
        self.assertEqual(out["shown_flag"], "yes")
        self.assertEqual(out["remove_idle"], "1", calls)
        self.assertEqual(out["watcher"], "dead")
        self.assertEqual(out["pidfile"], "no")
        self.assertEqual(out["flag_after"], "no")
        title_lines = [c for c in calls if c.startswith("notify:--tmux-icon ⏸️")]
        self.assertIn("make build", title_lines[0])
        # fake herdrはPATH解決で呼ばれる。HERDR_BIN_PATHに置いたPATH外のtrapが
        # 呼ばれたら、実装がPATH以外の経路（環境変数）でherdrを引いている。
        self.assertFalse(trapped, "trap herdr was invoked outside PATH")

    def test_screen_change_clears_icon_and_next_stall_notifies_again(self):
        out, calls, _ = self.run_script(
            "_notification_preexec 'make build'\n"
            "wait_for_count 'notify:--tmux-icon ⏸️' 1 || exit 1\n"
            'print changed > "$FAKE/screen"\n'
            "wait_for_count remove_idle 1 || exit 1\n"
            'print -r -- "flag_after_change=$([[ -f $pidfile.shown ]] && echo yes || echo no)"\n'
            # 画面が再び止まれば新しい停止として再通知される
            "wait_for_count 'notify:--tmux-icon ⏸️' 2 || exit 1\n"
            "_notification_precmd\n",
        )
        self.assertEqual(out["flag_after_change"], "no", calls)
        self.assertEqual(sum(c.startswith("notify:--tmux-icon ⏸️") for c in calls), 2, calls)

    def test_changing_screen_never_notifies(self):
        out, calls, _ = self.run_script(
            "_notification_preexec 'make build'\n"
            "local i\n"
            # 並列シャード下のスケジューリング揺らぎで偽陽性にならないよう、閾値に
            # 対し十分短い間隔で、原子的(mv)に更新し続ける
            "for i in {1..25}; do print $i > \"$FAKE/screen.tmp\"; mv \"$FAKE/screen.tmp\" \"$FAKE/screen\"; sleep 0.2; done\n"
            "_notification_precmd\n",
            env={"HERDR_IDLE_WATCH_SECONDS": "4"},
        )
        self.assertEqual(calls, [])

    def test_focused_pane_shows_nothing_until_focus_leaves(self):
        out, calls, _ = self.run_script(
            'print true > "$FAKE/focused"\n'
            "_notification_preexec 'make build'\n"
            "sleep 3.5\n"
            'print -r -- "while_focused=$(count_lines notify:)/$(count_lines update:)"\n'
            'print false > "$FAKE/focused"\n'
            "wait_for_count 'notify:--tmux-icon ⏸️' 1 || exit 1\n"
            # 表示中にフォーカスされたら外し、外れたら通知なしで再表示する
            'print true > "$FAKE/focused"\n'
            "wait_for_count remove_idle 1 || exit 1\n"
            'print false > "$FAKE/focused"\n'
            "wait_for_count 'update:⏸️' 1 || exit 1\n"
            'print -r -- "notify_total=$(count_lines notify:)"\n'
            "_notification_precmd\n",
        )
        self.assertEqual(out["while_focused"], "0/0", calls)
        self.assertEqual(out["notify_total"], "1", calls)

    def test_agent_pane_is_left_to_notify_rich(self):
        # AIペインの入力待ちはnotify-richの✋が担当する。ラッパー名（clo等）で
        # NOTIFY_COMMAND_EXCLUDEをすり抜けても、herdrのagent検出で出さない。
        out, calls, _ = self.run_script(
            "_notification_preexec 'clo'\n"
            "sleep 3.5\n"
            "_notification_precmd\n",
            files={"agent": "claude"},
        )
        self.assertEqual(calls, [])

    def test_prompt_wait_marker_is_not_overridden(self):
        # 同tabで自作プロンプトの✋が立っている間は、推測の⏸️で上書きしない
        out, calls, _ = self.run_script(
            "_notification_preexec 'make build'\n"
            "sleep 3.5\n"
            'print -r -- "flag=$([[ -f $pidfile.shown ]] && echo yes || echo no)"\n'
            "_notification_precmd\n",
            files={"marker": "✋\n"},
        )
        self.assertEqual(out["flag"], "no")
        self.assertEqual(calls, [])


class HerdrIdleWatchLifecycleTest(HerdrIdleWatchTestBase):
    def test_watcher_exits_when_pane_read_fails(self):
        out, calls, _ = self.run_script(
            "_notification_preexec 'make build'\n"
            'pid="$_herdr_idle_watch_pid"\n'
            "local i\n"
            "for i in {1..50}; do [[ -f $pidfile ]] || break; sleep 0.1; done\n"
            'print -r -- "pidfile=$([[ -f $pidfile ]] && echo yes || echo no)"\n'
            'print -r -- "watcher=$(alive $pid)"\n',
            files={"read_fail": "1"},
        )
        self.assertEqual(out["pidfile"], "no")
        self.assertEqual(out["watcher"], "dead")
        self.assertEqual(calls, [])

    def test_second_preexec_leaves_a_single_watcher(self):
        out, calls, _ = self.run_script(
            "_notification_preexec 'first'\n"
            'first="$_herdr_idle_watch_pid"\n'
            "_notification_preexec 'second'\n"
            'second="$_herdr_idle_watch_pid"\n'
            "sleep 1\n"
            'print -r -- "first=$(alive $first)"\n'
            'print -r -- "second=$(alive $second)"\n'
            "_notification_precmd\n"
            "sleep 0.3\n"
            'print -r -- "second_after=$(alive $second)"\n',
        )
        # pidfileの持ち主でなくなった監視は次の周回で自発的に終了する
        self.assertEqual(out["first"], "dead")
        self.assertEqual(out["second"], "alive")
        self.assertEqual(out["second_after"], "dead")

    def test_watcher_exits_after_parent_shell_dies(self):
        out, _, _ = self.run_script(
            "_notification_preexec 'make build'\n"
            'print -r -- "pid=$_herdr_idle_watch_pid"\n'
            "exit 0\n",
        )
        pid = int(out["pid"])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.2)
        os.kill(pid, signal.SIGTERM)
        self.fail("watcher survived its parent shell")

    def test_precmd_does_not_kill_when_pidfile_owner_changed(self):
        # 監視が先に終了した後にPIDが再利用された無関係プロセスを止めないため、
        # pidfileの持ち主が自分の起動PIDでなければkillしない。
        out, _, _ = self.run_script(
            "sleep 30 &!\n"
            'bystander=$!\n'
            "_notification_preexec 'make build'\n"
            'print $bystander > "$pidfile"\n'
            "_notification_precmd\n"
            'print -r -- "bystander=$(alive $bystander)"\n'
            'kill $bystander 2>/dev/null\n',
        )
        self.assertEqual(out["bystander"], "alive")


class HerdrIdleWatchSkipTest(HerdrIdleWatchTestBase):
    def test_watcher_is_not_started_when_out_of_scope(self):
        cases = [
            ("excluded command", "vim notes.txt", {}),
            ("excluded ssh", "ssh host", {}),
            ("outside herdr", "make build", {"HERDR_PANE_ID": None}),
            ("inside tmux", "make build", {"TMUX": "/tmp/tmux-1/default,1,0"}),
            ("shell launch zsh", "zsh", {}),
            ("shell launch bash by path", "/bin/bash -c true", {}),
            ("disable_notify", "make build", {"DISABLE_NOTIFY": "1"}),
            ("watch disabled", "make build", {"HERDR_IDLE_WATCH_SECONDS": "0"}),
        ]
        for name, command, env in cases:
            with self.subTest(name):
                out, calls, _ = self.run_script(
                    f"_notification_preexec '{command}'\n"
                    'print -r -- "pid=[$_herdr_idle_watch_pid]"\n'
                    'print -r -- "pidfile=$([[ -f $pidfile ]] && echo yes || echo no)"\n',
                    env=env,
                )
                self.assertEqual(out["pid"], "[]")
                self.assertEqual(out["pidfile"], "no")

    def test_control_case_starts_a_watcher(self):
        # 上の「起動しない」ケースが別の理由で通っていないことの対照
        out, _, _ = self.run_script(
            "_notification_preexec 'make build'\n"
            'print -r -- "has_pid=$([[ -n $_herdr_idle_watch_pid ]] && echo yes || echo no)"\n'
            'print -r -- "pidfile=$([[ -f $pidfile ]] && echo yes || echo no)"\n'
            "_notification_precmd\n",
        )
        self.assertEqual(out["has_pid"], "yes")
        self.assertEqual(out["pidfile"], "yes")


if __name__ == "__main__":
    unittest.main()
