import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
GIT_ALIASES = REPO_ROOT / "shell/zsh/alias/git.zsh"
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH, "zsh is required")
class WtmTest(unittest.TestCase):
    """wtm merges only from a clean secondary disposable worktree."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.target = self.root / "repository"
        self.source = self.root / "feature"
        self._initialize_repository()

    def tearDown(self):
        self.temp_dir.cleanup()

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.target,
            capture_output=True,
            text=True,
            check=check,
        )

    def _initialize_repository(self):
        self.git("init", str(self.target), cwd=self.root)
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        (self.target / "base.txt").write_text("base\n", encoding="utf-8")
        self.git("add", "base.txt")
        self.git("commit", "-m", "test: base")
        self.git("branch", "-M", "main")
        self.git("worktree", "add", "-b", "feature/login", str(self.source))
        (self.source / "feature.txt").write_text("feature\n", encoding="utf-8")
        self.git("add", "feature.txt", cwd=self.source)
        self.git("commit", "-m", "test: feature", cwd=self.source)

    def run_wtm(self, *args, cwd=None, setup_script="", extra_env=None):
        quoted_args = " ".join(shlex.quote(arg) for arg in args)
        script = f'''
            source "{GIT_ALIASES}"
            {setup_script}
            wtm {quoted_args}
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
            print -r -- "__PWD=$PWD"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=cwd or self.source,
            capture_output=True,
            text=True,
            env=os.environ | (extra_env or {}),
        )
        values = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__")
        }
        return result, values

    def assert_source_preserved(self):
        self.assertTrue(self.source.exists())
        self.assertEqual(
            self.git(
                "branch", "--format=%(refname:short)", "--list", "feature/login"
            ).stdout.strip(),
            "feature/login",
        )

    def assert_no_merge_started(self, original_target_head):
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), original_target_head)
        merge_head = self.git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False)
        self.assertNotEqual(merge_head.returncode, 0)
        self.assert_source_preserved()

    def test_fast_forward_updates_target_then_removes_source_and_branch(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()

        result, values = self.run_wtm("main")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__PWD"], str(self.target.resolve()))
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assertTrue((self.target / "feature.txt").exists())
        self.assertFalse(self.source.exists())
        self.assertEqual(self.git("branch", "--list", "feature/login").stdout, "")
        self.assertEqual(len(self.git("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()), 2)

    def test_diverged_history_creates_merge_commit_without_editor_then_cleans_up(self):
        (self.target / "main.txt").write_text("main\n", encoding="utf-8")
        self.git("add", "main.txt")
        self.git("commit", "-m", "test: main")
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        target_head = self.git("rev-parse", "HEAD").stdout.strip()

        result, values = self.run_wtm(
            "main", extra_env={"GIT_EDITOR": "false"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        merge_commit = self.git("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
        self.assertEqual(merge_commit[1:], [target_head, source_head])
        self.assertTrue((self.target / "main.txt").exists())
        self.assertTrue((self.target / "feature.txt").exists())
        self.assertFalse(self.source.exists())
        self.assertEqual(self.git("branch", "--list", "feature/login").stdout, "")

    def test_conflict_preserves_target_merge_state_source_and_branch(self):
        (self.target / "conflict.txt").write_text("base\n", encoding="utf-8")
        self.git("add", "conflict.txt")
        self.git("commit", "-m", "test: conflict base")
        self.git("merge", "main", cwd=self.source)
        (self.source / "conflict.txt").write_text("source\n", encoding="utf-8")
        self.git("add", "conflict.txt", cwd=self.source)
        self.git("commit", "-m", "test: source conflict", cwd=self.source)
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        (self.target / "conflict.txt").write_text("target\n", encoding="utf-8")
        self.git("add", "conflict.txt")
        self.git("commit", "-m", "test: target conflict")

        result, values = self.run_wtm("main")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(values["__STATUS"], "0")
        self.assertEqual(
            self.git("rev-parse", "MERGE_HEAD").stdout.strip(), source_head
        )
        self.assertIn("UU conflict.txt", self.git("status", "--porcelain").stdout)
        conflict = (self.target / "conflict.txt").read_text(encoding="utf-8")
        self.assertIn("<<<<<<< HEAD", conflict)
        self.assertIn("=======", conflict)
        self.assertIn(">>>>>>> ", conflict)
        self.assert_source_preserved()

    def test_source_branch_drift_before_merge_prevents_merge_and_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        drift_head = self.git("rev-parse", "main").stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            WTM_DRIFT_HEAD={shlex.quote(drift_head)}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "status" && "$4" == "--porcelain" ]]; then
                command git "$@"
                command git -C "$WTM_SOURCE_PATH" update-ref refs/heads/feature/login "$WTM_DRIFT_HEAD"
              else
                command git "$@"
              fi
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source branch changed before merge", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_source_worktree_head_drift_before_merge_prevents_merge_and_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        drift_head = self.git("rev-parse", "main").stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            WTM_DRIFT_HEAD={shlex.quote(drift_head)}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "status" && "$4" == "--porcelain" ]]; then
                command git "$@"
                command git -C "$WTM_SOURCE_PATH" switch --detach "$WTM_DRIFT_HEAD"
              else
                command git "$@"
              fi
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source worktree HEAD changed before merge", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_target_branch_drift_before_merge_prevents_merge_and_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "status" && "$4" == "--porcelain" ]]; then
                command git "$@"
                command git -C "$WTM_TARGET_PATH" switch --detach
              else
                command git "$@"
              fi
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("target worktree branch changed before merge", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_target_head_drift_before_merge_prevents_merge_and_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_DRIFT_HEAD={shlex.quote(source_head)}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "status" && "$4" == "--porcelain" ]]; then
                command git "$@"
                command git -C "$WTM_TARGET_PATH" update-ref refs/heads/main "$WTM_DRIFT_HEAD"
              else
                command git "$@"
              fi
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("target worktree HEAD changed before merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_target_branch_drift_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  command git -C "$WTM_TARGET_PATH" switch -c race/target
                fi
                return $merge_exit
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("target worktree branch changed after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_dirty_target_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  print -r -- dirty > "$WTM_TARGET_PATH/race-dirty.txt"
                fi
                return $merge_exit
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("target worktree changed after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_target_status_probe_failure_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        marker = self.root / "target-merge-finished"
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_MERGE_MARKER={shlex.quote(str(marker))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  print -r -- merged > "$WTM_MERGE_MARKER"
                fi
                return $merge_exit
              fi
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "status" && "$4" == "--porcelain" && -e "$WTM_MERGE_MARKER" ]]; then
                return 44
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "44", result.stderr)
        self.assertIn("failed to inspect target worktree status after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_source_worktree_branch_drift_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  command git -C "$WTM_SOURCE_PATH" switch -c race/source
                fi
                return $merge_exit
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source worktree branch changed after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_source_worktree_head_drift_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        drift_head = self.git("rev-parse", "main").stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            WTM_DRIFT_HEAD={shlex.quote(drift_head)}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  command git -C "$WTM_SOURCE_PATH" update-ref refs/heads/feature/login "$WTM_DRIFT_HEAD"
                fi
                return $merge_exit
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source worktree HEAD changed after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_source_status_probe_failure_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        marker = self.root / "merge-finished"
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            WTM_MERGE_MARKER={shlex.quote(str(marker))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  print -r -- merged > "$WTM_MERGE_MARKER"
                fi
                return $merge_exit
              fi
              if [[ "$1" == "-C" && "$2" == "$WTM_SOURCE_PATH" && "$3" == "status" && "$4" == "--porcelain" && -e "$WTM_MERGE_MARKER" ]]; then
                return 43
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "43", result.stderr)
        self.assertIn("failed to inspect source worktree status after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_source_branch_ref_drift_after_head_guard_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        drift_head = self.git("rev-parse", "main").stdout.strip()
        marker = self.root / "source-ref-merge-finished"
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            WTM_DRIFT_HEAD={shlex.quote(drift_head)}
            WTM_MERGE_MARKER={shlex.quote(str(marker))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  print -r -- merged > "$WTM_MERGE_MARKER"
                fi
                return $merge_exit
              fi
              if [[ "$1" == "-C" && "$2" == "$WTM_SOURCE_PATH" && "$3" == "status" && "$4" == "--porcelain" && -e "$WTM_MERGE_MARKER" ]]; then
                command git "$@"
                command git -C "$WTM_SOURCE_PATH" update-ref refs/heads/feature/login "$WTM_DRIFT_HEAD"
                return $?
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source branch changed after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_dirty_source_after_merge_stops_cleanup(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge" ]]; then
                command git "$@"
                local merge_exit=$?
                if [[ $merge_exit -eq 0 ]]; then
                  print -r -- dirty > "$WTM_SOURCE_PATH/race-dirty.txt"
                fi
                return $merge_exit
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source worktree changed after merge", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_failed_ancestor_guard_stops_cleanup_after_merge(self):
        source_head = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "merge-base" && "$4" == "--is-ancestor" ]]; then
                return 1
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("not an ancestor of target HEAD", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assert_source_preserved()

    def test_dirty_source_is_rejected_before_merge(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        (self.source / "dirty.txt").write_text("dirty\n", encoding="utf-8")

        result, values = self.run_wtm("main")

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source worktree has uncommitted changes", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_dirty_target_is_rejected_before_merge(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        (self.target / "dirty.txt").write_text("dirty\n", encoding="utf-8")

        result, values = self.run_wtm("main")

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("target worktree has uncommitted changes", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_source_status_probe_failure_prevents_merge_and_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        setup_script = f'''
            WTM_SOURCE_PATH={shlex.quote(str(self.source.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_SOURCE_PATH" && "$3" == "status" && "$4" == "--porcelain" ]]; then
                return 41
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "41", result.stderr)
        self.assertIn("failed to inspect source worktree status", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_target_status_probe_failure_prevents_merge_and_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        setup_script = f'''
            WTM_TARGET_PATH={shlex.quote(str(self.target.resolve()))}
            git() {{
              if [[ "$1" == "-C" && "$2" == "$WTM_TARGET_PATH" && "$3" == "status" && "$4" == "--porcelain" ]]; then
                return 42
              fi
              command git "$@"
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "42", result.stderr)
        self.assertIn("failed to inspect target worktree status", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_detached_source_is_rejected_without_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("switch", "--detach", cwd=self.source)

        result, values = self.run_wtm("main")

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("detached HEAD", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_primary_source_is_rejected_without_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()

        result, values = self.run_wtm("feature/login", cwd=self.target)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("primary worktree", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_same_source_and_target_branch_is_rejected_without_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()

        result, values = self.run_wtm("feature/login")

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("source and target branches must differ", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_missing_target_worktree_is_rejected_without_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()

        result, values = self.run_wtm("missing")

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("target branch is not checked out", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_multiple_target_worktrees_are_rejected_without_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()
        duplicate = shlex.quote(str(self.target.resolve()))
        setup_script = f'''
            git() {{
              if [[ "$1" == "worktree" && "$2" == "list" && "$3" == "--porcelain" ]]; then
                command git "$@"
                print -r -- ""
                print -r -- "worktree {duplicate}"
                print -r -- "HEAD duplicate"
                print -r -- "branch refs/heads/main"
              else
                command git "$@"
              fi
            }}
        '''

        result, values = self.run_wtm("main", setup_script=setup_script)

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("multiple worktrees", result.stderr)
        self.assert_no_merge_started(target_head)

    def test_invalid_argument_counts_return_usage_without_cleanup(self):
        target_head = self.git("rev-parse", "HEAD").stdout.strip()

        for args in [(), ("",), ("main", "extra")]:
            with self.subTest(args=args):
                result, values = self.run_wtm(*args)

                self.assertEqual(values["__STATUS"], "2", result.stderr)
                self.assertIn("Usage: wtm <target-branch>", result.stderr)
                self.assert_no_merge_started(target_head)


if __name__ == "__main__":
    unittest.main()
