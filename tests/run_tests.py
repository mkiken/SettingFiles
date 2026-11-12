#!/usr/bin/env python3
"""Run the unittest suite in deterministic parallel shards."""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
DEPENDENCY_MAP_PATH = TEST_DIR / "dependencies.toml"
MAX_DEFAULT_JOBS = 8

sys.path.insert(0, str(TEST_DIR))
from support import purge_multiplexer_env  # noqa: E402


@dataclass
class ShardRun:
    index: int
    test_ids: list
    process: subprocess.Popen
    output_file: object
    started_at: float


@dataclass
class ShardResult:
    index: int
    test_count: int
    returncode: int
    duration: float
    output: str


class ShardLaunchError(RuntimeError):
    pass


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("jobs must be an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("jobs must be greater than zero")
    return parsed


def default_job_count(cpu_count):
    return min(MAX_DEFAULT_JOBS, cpu_count or 1)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=default_job_count(os.cpu_count()),
        help="number of parallel test processes (default: min(8, CPU count))",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--paths",
        nargs="+",
        metavar="PATH",
        help="repo-relative changed paths; runs only convention-mapped tests",
    )
    selection.add_argument("--changed", action="store_true", help="select Git changes")
    parser.add_argument("--base", help="include changes since this commit (requires --changed)")
    parser.add_argument("--list-details", action="store_true", help="show all selection details")
    args = parser.parse_args(argv)
    if args.base and not args.changed:
        parser.error("--base requires --changed")
    return args


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def discover_test_ids(test_dir=TEST_DIR):
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(test_dir),
        pattern="test_*.py",
        top_level_dir=str(test_dir),
    )
    tests = list(iter_tests(suite))
    modules = {test.__class__.__module__ for test in tests}
    missing = sorted(test_module_name(path, test_dir) for path in test_dir.rglob("test_*.py")
                     if test_module_name(path, test_dir) not in modules)
    if loader.errors or missing:
        raise ValueError("Test discovery failed: " + "; ".join(loader.errors + missing))
    return sorted(test.id() for test in tests)


def changed_paths(base=None, root=REPO_ROOT):
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            raise ValueError(f"Git change detection failed: {error}") from error
    diff = git("diff", "--name-status", "-z", "--no-renames", base or "HEAD", "--").split(b"\0")
    entries = list(zip(diff[0::2], diff[1::2]))
    paths = {os.fsdecode(name) for status, name in entries if status and name}
    paths.update(os.fsdecode(name) for name in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if name)
    return sorted(paths), any(status == b"D" for status, name in entries)


def requires_full_suite(paths, deleted=False):
    return deleted or any(path in {"tests/run_tests.py", "tests/support.py", "tests/dependencies.toml"}
                          or (path.startswith("tests/") and path.endswith("/__init__.py")) for path in paths)


def normalize_name(value):
    normalized = []
    previous_separator = False
    for character in value.lower():
        if character.isalnum() or character == "_":
            normalized.append(character)
            previous_separator = False
        elif not previous_separator:
            normalized.append("_")
            previous_separator = True
    return "".join(normalized).strip("_")


def normalize_directory(value):
    if value.startswith("."):
        value = f"dot_{value[1:]}"
    return normalize_name(value)


def normalize_repo_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        raise ValueError(f"path must be repo-relative: {value}")
    return path


def test_path_prefix_for_source(source_path, test_dir=TEST_DIR):
    source = normalize_repo_path(str(source_path))
    parts = source.parts
    parent_parts = parts[1:-1] if parts[0] == "tests" else parts[:-1]
    filename = parts[-1]
    if filename.endswith(".py"):
        filename = filename[:-3]
    filename = normalize_name(filename)
    parent = test_dir.joinpath(*(normalize_directory(part) for part in parent_parts))
    return parent / f"test_{filename}"


def test_module_name(test_path, test_dir=TEST_DIR):
    return ".".join(test_path.relative_to(test_dir).with_suffix("").parts)


def load_dependency_map(map_path=DEPENDENCY_MAP_PATH, root=REPO_ROOT, test_ids=None):
    with map_path.open("rb") as map_file:
        data = tomllib.load(map_file)
    if set(data) - {"extra_tests", "untested"}:
        raise ValueError("dependencies.toml has unknown tables")
    entries = data.get("extra_tests", {})
    untested = data.get("untested", {})
    if not isinstance(entries, dict):
        raise ValueError("dependencies.toml [extra_tests] must be a table")
    if any(
        not isinstance(source, str)
        or not isinstance(test_paths, list)
        or any(not isinstance(test_path, str) for test_path in test_paths)
        for source, test_paths in entries.items()
    ):
        raise ValueError("dependencies.toml entries must map paths to string lists")
    if not isinstance(untested, dict) or any(not isinstance(reason, str) or not reason.strip() for reason in untested.values()):
        raise ValueError("dependencies.toml [untested] must map paths to nonempty reasons")
    for source in list(entries) + list(untested):
        if str(normalize_repo_path(source)) != source:
            raise ValueError(f"invalid dependency path: {source}")
        if (root / source).is_dir():
            raise ValueError(f"dependency path must name a file: {source}")
    if set(entries) & set(untested):
        raise ValueError("dependencies.toml entries overlap exclusions")
    for source in untested:
        selected, _ = selected_test_paths([source], root / "tests", {})
        if selected:
            raise ValueError(f"exclusion overlaps tests: {source}")
    modules = {test_id.rsplit(".", 2)[0] for test_id in test_ids} if test_ids is not None else None
    for source, targets in entries.items():
        if not targets or len(targets) != len(set(targets)):
            raise ValueError(f"invalid dependency targets: {source}")
        for target in targets:
            normalized = normalize_repo_path(target)
            test_path = root / normalized
            if (str(normalized) != target or not target.startswith("tests/")
                    or not test_path.name.startswith("test_") or test_path.suffix != ".py"
                    or not test_path.is_file()):
                raise ValueError(f"dependencies.toml references missing tests: {target}")
            if modules is not None and test_module_name(test_path, root / "tests") not in modules:
                raise ValueError(f"dependencies.toml references uncollected test: {target}")
    return entries, untested


def selected_test_paths(source_paths, test_dir=TEST_DIR, dependency_map=None):
    dependency_map = dependency_map if dependency_map is not None else load_dependency_map()[0]
    selected = set()
    unmatched = []
    for source_value in source_paths:
        source = normalize_repo_path(str(source_value))
        source_string = source.as_posix()
        direct = []
        source_file = REPO_ROOT / source
        if source_string.startswith("tests/") and source_file.name.startswith("test_") and source_file.suffix == ".py":
            direct.append(source_file)
        else:
            prefix = test_path_prefix_for_source(source, test_dir)
            direct.extend([prefix.with_suffix(".py"), *sorted(prefix.parent.glob(f"{prefix.name}__*.py"))])
        mapped = [REPO_ROOT / normalize_repo_path(path) for path in dependency_map.get(source_string, [])]
        missing_mapped = [path for path in mapped if not path.is_file()]
        if missing_mapped:
            raise ValueError(
                "dependencies.toml references missing tests: "
                + ", ".join(str(path.relative_to(REPO_ROOT)) for path in missing_mapped)
            )
        candidates = direct + mapped
        existing = [path for path in candidates if path.is_file()]
        if not existing:
            unmatched.append(source_string)
        selected.update(existing)
    return sorted(selected), unmatched


def select_test_ids(source_paths, test_ids, test_dir=TEST_DIR, dependency_map=None):
    paths, unmatched = selected_test_paths(source_paths, test_dir, dependency_map)
    modules = {test_module_name(path, test_dir) for path in paths}
    selected = [
        test_id
        for test_id in test_ids
        if any(test_id.startswith(f"{module}.") for module in modules)
    ]
    return sorted(selected), paths, unmatched


def partition_test_ids(test_ids, jobs):
    sorted_ids = sorted(test_ids)
    shard_count = min(jobs, len(sorted_ids))
    shards = [[] for _ in range(shard_count)]
    for index, test_id in enumerate(sorted_ids):
        shards[index % shard_count].append(test_id)
    return shards


def terminate_processes(runs, grace_seconds=2.0):
    active = [run.process for run in runs if run.process.poll() is None]
    for process in active:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + grace_seconds
    while active and time.monotonic() < deadline:
        active = [process for process in active if process.poll() is None]
        if active:
            time.sleep(0.05)

    for process in active:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    for process in active:
        process.wait()


def close_outputs(runs):
    for run in runs:
        run.output_file.close()


def run_shards(
    shards,
    test_dir=TEST_DIR,
    python_executable=sys.executable,
    popen_factory=subprocess.Popen,
    stop_processes=terminate_processes,
):
    runs = []
    try:
        for index, test_ids in enumerate(shards, start=1):
            output_file = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            try:
                process = popen_factory(
                    [python_executable, "-m", "unittest", *test_ids],
                    cwd=str(test_dir),
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=True,
                )
            except OSError as error:
                output_file.close()
                stop_processes(runs)
                raise ShardLaunchError(f"failed to start shard {index}: {error}") from error
            runs.append(
                ShardRun(
                    index=index,
                    test_ids=test_ids,
                    process=process,
                    output_file=output_file,
                    started_at=time.monotonic(),
                )
            )

        pending = list(runs)
        results = []
        while pending:
            for run in list(pending):
                returncode = run.process.poll()
                if returncode is None:
                    continue
                run.output_file.seek(0)
                results.append(
                    ShardResult(
                        index=run.index,
                        test_count=len(run.test_ids),
                        returncode=returncode,
                        duration=time.monotonic() - run.started_at,
                        output=run.output_file.read(),
                    )
                )
                pending.remove(run)
            if pending:
                time.sleep(0.05)
        return sorted(results, key=lambda result: result.index)
    except KeyboardInterrupt:
        stop_processes(runs)
        raise
    finally:
        close_outputs(runs)


def print_results(results, total_duration):
    failed = [result for result in results if result.returncode != 0]
    for result in results:
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(
            f"{status} shard {result.index}: "
            f"{result.test_count} tests in {result.duration:.3f}s"
        )
    print(
        f"Ran {sum(result.test_count for result in results)} tests "
        f"across {len(results)} shards in {total_duration:.3f}s"
    )

    for result in failed:
        print(f"\n--- shard {result.index} diagnostics ---", file=sys.stderr)
        print(result.output.rstrip(), file=sys.stderr)
    return 1 if failed else 0


def main(argv=None):
    args = parse_args(argv)
    # Herdr/tmux pane 内でスイートを起動すると注入変数を全 shard が継承する。
    # テストの PATH スタブは HERDR_BIN_PATH 優先の実装を迂回できないため
    # ここで一度だけ落とす。
    purge_multiplexer_env()
    try:
        test_ids = discover_test_ids()
        dependencies, untested = load_dependency_map(test_ids=test_ids)
        paths, deleted = changed_paths(args.base) if args.changed else (args.paths, False)
        if paths is not None:
            if not paths:
                print("No changed paths; no tests run")
                return 0
            selected, selected_paths, unmatched = select_test_ids(paths, test_ids, dependency_map=dependencies)
            excluded = {path: untested[path] for path in unmatched if path in untested}
            unmatched = [path for path in unmatched if path not in excluded]
            details = []
            for path in paths:
                if path in excluded:
                    details.append(f"{path!r}: excluded: {excluded[path]!r}")
                elif path in unmatched:
                    details.append(f"{path!r}: no mapped tests")
                else:
                    mapped, _ = selected_test_paths([path], dependency_map=dependencies)
                    reasons = []
                    if selected_test_paths([path], dependency_map={})[0]:
                        reasons.append("naming convention")
                    if path in dependencies:
                        reasons.append("extra dependency")
                    reason = " and ".join(reasons)
                    details.append(f"{path!r}: {reason}: " + ", ".join(str(p.relative_to(REPO_ROOT)) for p in mapped))
            print(f"Paths: {len(paths)}; selected modules: {len(selected_paths)}; tests: {len(selected)}; excluded: {len(excluded)}; unmapped: {len(unmatched)}")
            if args.list_details or (len(details) <= 100 and sum(len(line) for line in details) <= 8192 and all(len(line) <= 1000 for line in details)):
                for line in details:
                    print(line)
            else:
                print("Use --list-details to show selection details")
            if unmatched:
                return 2
            if requires_full_suite(paths, deleted or any(not (REPO_ROOT / path).exists() for path in paths)):
                print("Running full suite: shared test infrastructure or deletion")
            else:
                test_ids = selected
                if not test_ids:
                    print("No tests selected; no tests run")
                    return 0
    except (ValueError, OSError, tomllib.TOMLDecodeError) as error:
        print(error, file=sys.stderr)
        return 2
    if not test_ids:
        print("No tests discovered", file=sys.stderr)
        return 1

    shards = partition_test_ids(test_ids, args.jobs)
    print(
        f"Discovered {len(test_ids)} tests; starting {len(shards)} shards",
        flush=True,
    )
    started_at = time.monotonic()
    try:
        results = run_shards(shards)
    except ShardLaunchError as error:
        print(error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; all test processes stopped", file=sys.stderr)
        return 130
    return print_results(results, time.monotonic() - started_at)


if __name__ == "__main__":
    sys.exit(main())
