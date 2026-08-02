import io
import os
import signal
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_tests


class RunTestsTest(unittest.TestCase):
    def create_test_file(self, test_dir, relative_path, class_name="ExampleTest"):
        path = test_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "import unittest\n"
            f"class {class_name}(unittest.TestCase):\n"
            "    def test_example(self): pass\n"
        )
        return path

    def test_discovers_each_test_once_in_stable_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            (test_dir / "test_zeta.py").write_text(
                "import unittest\n"
                "class ZetaTest(unittest.TestCase):\n"
                "    def test_second(self): pass\n"
            )
            (test_dir / "test_alpha.py").write_text(
                "import unittest\n"
                "class AlphaTest(unittest.TestCase):\n"
                "    def test_first(self): pass\n"
            )

            test_ids = run_tests.discover_test_ids(test_dir)

        self.assertEqual(
            test_ids,
            [
                "test_alpha.AlphaTest.test_first",
                "test_zeta.ZetaTest.test_second",
            ],
        )

    def test_partitions_all_ids_once_with_balanced_deterministic_shards(self):
        test_ids = [f"test_module.ExampleTest.test_{index:02d}" for index in range(19)]

        first = run_tests.partition_test_ids(reversed(test_ids), jobs=8)
        second = run_tests.partition_test_ids(test_ids, jobs=8)

        self.assertEqual(first, second)
        self.assertEqual(sorted(test_id for shard in first for test_id in shard), test_ids)
        self.assertEqual(len(set(test_id for shard in first for test_id in shard)), 19)
        self.assertLessEqual(max(map(len, first)) - min(map(len, first)), 1)

    def test_default_job_count_is_capped_and_handles_unknown_cpu_count(self):
        cases = ((16, 8), (4, 4), (None, 1))
        for cpu_count, expected in cases:
            with self.subTest(cpu_count=cpu_count):
                self.assertEqual(run_tests.default_job_count(cpu_count), expected)

    def test_explicit_job_count_overrides_default(self):
        self.assertEqual(run_tests.parse_args(["--jobs", "12"]).jobs, 12)

    def test_non_positive_job_count_is_rejected(self):
        for value in ("0", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(SystemExit):
                    with mock.patch("sys.stderr", io.StringIO()):
                        run_tests.parse_args(["--jobs", value])

    def test_paths_argument_accepts_multiple_repo_relative_paths(self):
        args = run_tests.parse_args(
            ["--paths", "shell/tmux/example.sh", "mac/scripts/example.sh"]
        )

        self.assertEqual(args.paths, ["shell/tmux/example.sh", "mac/scripts/example.sh"])

    def test_source_path_convention_preserves_extension_and_scenarios(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            direct = self.create_test_file(test_dir, "shell/tmux/test_example_sh.py", "DirectTest")
            scenario = self.create_test_file(
                test_dir,
                "shell/tmux/test_example_sh__edge_case.py",
                "ScenarioTest",
            )

            selected, unmatched = run_tests.selected_test_paths(
                ["shell/tmux/example.sh"],
                test_dir=test_dir,
                dependency_map={},
            )

        self.assertEqual(selected, [direct, scenario])
        self.assertEqual(unmatched, [])

    def test_python_and_dot_directories_have_deterministic_test_paths(self):
        self.assertEqual(
            run_tests.test_path_prefix_for_source("shell/tmux/example.py"),
            run_tests.TEST_DIR / "shell" / "tmux" / "test_example",
        )
        self.assertEqual(
            run_tests.test_path_prefix_for_source(".claude/skills/worktree-task/SKILL.md"),
            run_tests.TEST_DIR
            / "dot_claude"
            / "skills"
            / "worktree_task"
            / "test_skill_md",
        )

    def test_select_test_ids_deduplicates_direct_and_dependency_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            test_dir = repo_root / "tests"
            test_file = self.create_test_file(test_dir, "shell/test_example_sh.py")
            test_ids = ["shell.test_example_sh.ExampleTest.test_example"]
            with mock.patch.object(run_tests, "REPO_ROOT", repo_root):
                selected, paths, unmatched = run_tests.select_test_ids(
                    ["shell/example.sh"],
                    test_ids,
                    test_dir=test_dir,
                    dependency_map={"shell/example.sh": ["tests/shell/test_example_sh.py"]},
                )

        self.assertEqual(selected, test_ids)
        self.assertEqual(paths, [test_file])
        self.assertEqual(unmatched, [])

    def test_unmapped_paths_and_invalid_dependency_targets_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            test_dir = repo_root / "tests"
            with mock.patch.object(run_tests, "REPO_ROOT", repo_root):
                selected, paths, unmatched = run_tests.select_test_ids(
                    ["shell/no_test.sh"], [], test_dir=test_dir, dependency_map={}
                )
                self.assertEqual((selected, paths, unmatched), ([], [], ["shell/no_test.sh"]))
                with self.assertRaisesRegex(ValueError, "missing tests"):
                    run_tests.selected_test_paths(
                        ["shell/example.sh"],
                        test_dir=test_dir,
                        dependency_map={"shell/example.sh": ["tests/missing.py"]},
                    )

        with self.assertRaises(ValueError):
            run_tests.normalize_repo_path("../outside.sh")

    def test_result_status_preserves_single_and_multiple_failures(self):
        success = run_tests.ShardResult(1, 2, 0, 0.1, "ok")
        failure_one = run_tests.ShardResult(2, 2, 1, 0.1, "first failure")
        failure_two = run_tests.ShardResult(3, 2, 2, 0.1, "second failure")
        cases = (
            ([success], 0, ""),
            ([success, failure_one], 1, "first failure"),
            ([failure_one, failure_two], 1, "second failure"),
        )
        for results, expected_status, expected_diagnostic in cases:
            with self.subTest(result_count=len(results), status=expected_status):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
                    status = run_tests.print_results(results, total_duration=0.2)
                self.assertEqual(status, expected_status)
                self.assertIn(expected_diagnostic, stderr.getvalue())

    def test_launch_failure_stops_started_shards(self):
        started_process = mock.Mock()
        started_process.pid = 123
        output = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        calls = 0

        def popen_factory(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                kwargs["stdout"].close()
                return started_process
            raise OSError("launch failed")

        stopped = []
        with mock.patch.object(tempfile, "TemporaryFile", return_value=output):
            with self.assertRaisesRegex(run_tests.ShardLaunchError, "shard 2"):
                run_tests.run_shards(
                    [["test_one"], ["test_two"]],
                    popen_factory=popen_factory,
                    stop_processes=lambda runs: stopped.extend(runs),
                )

        self.assertEqual([run.process for run in stopped], [started_process])

    def test_keyboard_interrupt_stops_all_started_shards(self):
        processes = []

        def popen_factory(*args, **kwargs):
            process = mock.Mock()
            process.pid = len(processes) + 100
            process.poll.side_effect = KeyboardInterrupt
            processes.append(process)
            return process

        stopped = []
        with self.assertRaises(KeyboardInterrupt):
            run_tests.run_shards(
                [["test_one"], ["test_two"]],
                popen_factory=popen_factory,
                stop_processes=lambda runs: stopped.extend(runs),
            )

        self.assertEqual([run.process for run in stopped], processes)

    def test_terminate_processes_signals_each_process_group(self):
        process = mock.Mock()
        process.pid = 456
        process.poll.side_effect = (None, 0)
        run = mock.Mock(process=process)

        with mock.patch.object(os, "killpg") as killpg:
            run_tests.terminate_processes([run], grace_seconds=1)

        killpg.assert_called_once_with(456, signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
