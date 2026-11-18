"""shell/zsh/alias/utils.zsh の confirm() が端末の残留入力を回答として誤読しないことのテスト。

前段の `--single-key` プロンプトで押した Enter や、make 実行中に打ったキーが
端末バッファに残っていると、後続の `read -r` がそれを即座に読んで No 扱いになる。
confirm() は stdin が端末のとき、プロンプト表示前にその残留入力を捨てる。
実端末が必要なため pty 経由で検証する。
"""
import os
import pty
import select
import subprocess
import time
import unittest

from support import REPO_ROOT, sanitized_env

STUBS = (
    '_start_prompt_wait_notification() { :; }\n'
    '_finish_prompt_wait_notification() { :; }\n'
)


def run_confirm_in_pty(confirm_args: str, answer: bytes) -> tuple[int, str]:
    """sleep 中に改行（残留入力）を送り、プロンプト表示後に answer を送る。"""
    script = (
        f"{STUBS}"
        'source shell/zsh/alias/utils.zsh; '
        'sleep 1; '
        f'confirm {confirm_args}; '
        'print -r -- "rc=$?"'
    )
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env=sanitized_env(HOME="/nonexistent"),
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    output = b""
    try:
        # sleep 中に押された Enter を模した残留入力
        os.write(master, b"\n")
        answered = False
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
            if not answered and (b"[y/N]" in output):
                os.write(master, answer)
                answered = True
            if b"rc=" in output and output.rstrip().split(b"rc=")[-1][:1].isdigit():
                break
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)
    text = output.decode("utf-8", errors="replace")
    rc_line = [line for line in text.splitlines() if line.strip().startswith("rc=")]
    if not rc_line:
        raise AssertionError(f"rc が出力に無い: {text!r}")
    return int(rc_line[-1].strip().removeprefix("rc=")), text


class ConfirmStaleInputTest(unittest.TestCase):
    def test_stale_newline_does_not_cancel_then_y_accepts(self):
        rc, out = run_confirm_in_pty('"続行しますか?"', b"y\n")
        self.assertEqual(rc, 0, out)

    def test_stale_newline_then_n_declines(self):
        rc, out = run_confirm_in_pty('"続行しますか?"', b"n\n")
        self.assertEqual(rc, 1, out)

    def test_stale_newline_single_key_then_y_accepts(self):
        rc, out = run_confirm_in_pty('"続行しますか?" --single-key', b"y")
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
