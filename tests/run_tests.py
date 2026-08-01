#!/usr/bin/env python3
"""Run the unittest suite in deterministic parallel shards."""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
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
