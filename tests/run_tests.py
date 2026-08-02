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
    parser.add_argument(
        "--paths",
        nargs="+",
        metavar="PATH",
        help="repo-relative changed paths; runs only convention-mapped tests",
    )
    return parser.parse_args(argv)


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def discover_test_ids(test_dir=TEST_DIR):
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(test_dir),
        pattern="test_*.py",
        top_level_dir=str(test_dir),
    )
    return sorted(test.id() for test in iter_tests(suite))


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
    path = PurePosixPath(value.replace("\\", "/"))
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


def load_dependency_map(map_path=DEPENDENCY_MAP_PATH):
    if not map_path.exists():
        return {}
    with map_path.open("rb") as map_file:
        data = tomllib.load(map_file)
    entries = data.get("extra_tests", {})
    if not isinstance(entries, dict):
        raise ValueError("dependencies.toml [extra_tests] must be a table")
    if any(
        not isinstance(source, str)
        or not isinstance(test_paths, list)
        or any(not isinstance(test_path, str) for test_path in test_paths)
        for source, test_paths in entries.items()
    ):
        raise ValueError("dependencies.toml entries must map paths to string lists")
    return entries


def selected_test_paths(source_paths, test_dir=TEST_DIR, dependency_map=None):
    dependency_map = dependency_map if dependency_map is not None else load_dependency_map()
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
    test_ids = discover_test_ids()
    if args.paths:
        try:
            test_ids, selected_paths, unmatched = select_test_ids(args.paths, test_ids)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
        print(
            f"Selected {len(test_ids)} tests from {len(selected_paths)} test modules",
            flush=True,
        )
        if unmatched:
            print(f"No mapped tests: {', '.join(unmatched)}", file=sys.stderr)
        if not test_ids:
            return 0
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
