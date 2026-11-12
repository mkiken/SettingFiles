# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit==0.15.2"]
# ///

import copy
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

import tomlkit


EXCLUDED = {("projects",), ("hooks", "state"), ("tui", "screen_reader_detection_done"),
            ("tui", "model_availability_nux")}


def plain(value):
    if hasattr(value, "unwrap"):
        value = value.unwrap()
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
        return value.isoformat()
    return value


def filtered(value, path=()):
    return {key: filtered(item, path + (key,)) if isinstance(item, dict) else item
            for key, item in value.items() if path + (key,) not in EXCLUDED}


def same(left, right):
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def restore_value(value, *candidates):
    for candidate in candidates:
        if candidate is not None and same(plain(candidate), value):
            return copy.deepcopy(candidate)
    if isinstance(value, dict):
        return {key: restore_value(item, *(candidate.get(key) for candidate in candidates
                                          if isinstance(plain(candidate), dict)))
                for key, item in value.items()}
    if isinstance(value, list):
        originals = [item for candidate in candidates if isinstance(candidate, list) for item in candidate]
        return [restore_value(item, *originals) for item in value]
    return value


def update_table(target, desired, source, path=()):
    for key in list(target):
        if path + (key,) not in EXCLUDED and key not in desired:
            child_path = path + (key,)
            if isinstance(plain(target[key]), dict) and any(
                excluded[:len(child_path)] == child_path for excluded in EXCLUDED
            ):
                update_table(target[key], {}, {}, child_path)
            else:
                del target[key]
    for key, value in desired.items():
        if isinstance(value, dict) and key in target and isinstance(plain(target[key]), dict):
            update_table(target[key], value, source.get(key, {}), path + (key,))
        elif key not in target or not same(plain(target[key]), value):
            candidate = source.get(key)
            target[key] = restore_value(value, candidate, target.get(key))


def main(live_path, repo_path, utils_path):
    live_text = live_path.read_text()
    original_text = repo_path.read_text()
    tomllib.loads(live_text)
    tomllib.loads(original_text)
    live = tomlkit.parse(live_text)
    repo = tomlkit.parse(original_text)
    source = filtered(plain(live))
    destination = filtered(plain(repo))
    with tempfile.TemporaryDirectory(prefix="codex-config-sync-") as directory:
        src_json = Path(directory) / "live.json"
        dst_json = Path(directory) / "repo.json"
        src_json.write_text(json.dumps(source, indent=2, allow_nan=False))
        dst_json.write_text(json.dumps(destination, indent=2, allow_nan=False))
        subprocess.run(["zsh", "-fc", 'source "$1" && smart_merge_json "$2" "$3" "$4" "$5"',
                        "zsh", str(utils_path), str(src_json), str(dst_json),
                        str(live_path), str(repo_path)], check=True)
        result = json.loads(dst_json.read_text())
    if same(result, destination):
        return
    update_table(repo, result, live)
    output = tomlkit.dumps(repo)
    tomllib.loads(output)
    with tempfile.NamedTemporaryFile(mode="w", dir=repo_path.parent, delete=False) as temporary:
        temporary.write(output)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(repo_path.stat().st_mode)
        os.replace(temporary_path, repo_path)
    finally:
        temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main(*(Path(arg).expanduser() for arg in sys.argv[1:]))
