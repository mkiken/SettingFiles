#!/usr/bin/env python3
"""Publish Codex monthly credit on Herdr pane events, without model requests."""

import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time


SOURCE = "codex-monthly-credit"
TOKEN = "monthly_credit"
TIMEOUT = 8
CACHE_SECONDS = 60


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def percent(value):
    return number(value) and 0 <= value <= 100


def read_credit(env):
    process = subprocess.Popen(
        ["codex", "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=env, start_new_session=True,
    )
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + TIMEOUT
            buffer = b""

            def send(message):
                process.stdin.write((json.dumps(message) + "\n").encode())
                process.stdin.flush()

            send({"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": SOURCE, "version": "0.1.0"}}})
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError("Codex credit read timed out")
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise ValueError("Codex closed its output")
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise ValueError("Invalid Codex response")
                    if message.get("id") not in (1, 2):
                        continue
                    if "error" in message:
                        raise ValueError("Codex credit API failed")
                    if message["id"] == 1:
                        send({"method": "initialized"})
                        send({"id": 2, "method": "account/rateLimits/read"})
                    else:
                        credit = message["result"]["rateLimits"]["individualLimit"]
                        if not isinstance(credit, dict):
                            raise ValueError("Missing monthly credit")
                        value = credit["remainingPercent"]
                        resets_at = credit.get("resetsAt")
                        if not percent(value) or not number(resets_at) or resets_at <= 0:
                            raise ValueError("Invalid monthly credit")
                        return value, resets_at
    finally:
        # The JS launcher can have a native child; terminate the whole new group.
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=1)
        except ProcessLookupError:
            process.wait()
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.stdin.close()
        process.stdout.close()


def cached_credit(env):
    cache_dir = Path(env.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "herdr-codex-monthly"
    cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    codex_home = Path(env.get("CODEX_HOME") or Path.home() / ".codex").resolve()
    key = hashlib.sha256(str(codex_home).encode()).hexdigest()
    cache_path = cache_dir / (key + ".json")
    with (cache_dir / (key + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = time.time()
        try:
            cache = json.loads(cache_path.read_text())
            fetched = cache["fetched_at"]
            value = cache["remaining_percent"]
            reset = cache["resets_at"]
            valid = (value is None and reset is None) or (
                percent(value) and number(reset) and reset > now)
            if number(fetched) and 0 <= now - fetched < CACHE_SECONDS and valid:
                return value
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            value, reset = read_credit(env)
        except (OSError, ValueError, KeyError, TypeError, TimeoutError):
            value, reset = None, None
        cache = {"fetched_at": time.time(), "remaining_percent": value, "resets_at": reset}
        with tempfile.NamedTemporaryFile(mode="w", dir=cache_dir, delete=False) as handle:
            temporary = Path(handle.name)
            try:
                json.dump(cache, handle)
                handle.flush()
                os.replace(temporary, cache_path)
            finally:
                temporary.unlink(missing_ok=True)
        return value


def refresh_usagebar(run, env, pane_id):
    plugins = json.loads(run(["plugin", "list", "--plugin", "usagebar", "--json"]).stdout)
    plugin = next(p for p in plugins["result"]["plugins"] if p["plugin_id"] == "usagebar" and p["enabled"])
    action = next(a for a in plugin["actions"] if a["id"] == "refresh")
    command = action["command"]
    if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
        raise ValueError("Invalid usagebar refresh command")
    # Keep notify-rich's config/state directories out of the other plugin.
    refresh_env = {key: value for key, value in env.items() if not key.startswith("HERDR_PLUGIN_")}
    refresh_env.update(HERDR_PANE_ID=pane_id, HERDR_PLUGIN_ACTION_ID="refresh")
    subprocess.run(command, cwd=plugin["plugin_root"], env=refresh_env,
                   capture_output=True, check=True, timeout=TIMEOUT)


def main():
    env = os.environ.copy()
    env["PATH"] = env.get("PATH", os.defpath) + ":/opt/homebrew/bin:/usr/local/bin"
    herdr = env.get("HERDR_BIN_PATH") or "herdr"
    event = json.loads(env.get("HERDR_PLUGIN_EVENT_JSON") or "{}")
    if not isinstance(event, dict) or not isinstance(event.get("data", {}), dict):
        return
    data = event.get("data", {})
    event_pane = data.get("pane")
    pane_id = env.get("HERDR_PANE_ID") or data.get("pane_id")
    if not pane_id and isinstance(event_pane, dict):
        pane_id = event_pane.get("pane_id")
    if not isinstance(pane_id, str) or not pane_id:
        return

    def run(arguments):
        return subprocess.run([herdr] + arguments, env=env, capture_output=True,
                              check=True, timeout=TIMEOUT)

    value = None
    context = None
    is_codex = False
    try:
        pane = json.loads(run(["pane", "get", pane_id]).stdout)["result"]["pane"]
        is_codex = pane.get("agent") == "codex"
        if is_codex:
            value = cached_credit(env)
            refreshed = False
            try:
                refresh_usagebar(run, env, pane_id)
                refreshed = True
            except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError):
                pass
            # A slow read may finish after the pane changed occupants.
            pane = json.loads(run(["pane", "get", pane_id]).stdout)["result"]["pane"]
            is_codex = pane.get("agent") == "codex"
            if not is_codex:
                value = None
            elif refreshed:
                context = pane.get("tokens", {}).get("context")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        value, context = None, None
    arguments = ["pane", "report-metadata", pane_id, "--source", SOURCE]
    arguments += ["--clear-token", "context_icon"]
    if isinstance(context, str) and context:
        arguments += ["--token", "context_compact=💬" + context]
    else:
        arguments += ["--clear-token", "context_compact"]
    if value is None:
        arguments += ["--clear-token", TOKEN]
    else:
        arguments += ["--agent", "codex", "--token", "{}=📅{:g}%".format(TOKEN, 100 - value)]
    run(arguments)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        # Event failures must not interfere with the independent notification hook.
        pass
