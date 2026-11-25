import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"

# 引数をstderrへ吐くfake filter（--bindの有無を検証する）
FAKE_FILTER_ECHO_ARGS = (
    "filter() {\n"
    '  local a; for a in "$@"; do print -r -- "ARG:$a" >&2; done\n'
    "  print -r -- $'/repo\\t/repo\\trepo\\tmain'\n"
    "}\n"
)

FAKE_GIT = (
    "git() {\n"
    '  if [[ "$1 $2" == "worktree list" ]]; then\n'
    "    printf 'worktree /repo\\nbranch refs/heads/main\\n\\n'\n"
    "    printf 'worktree /repo.wt-a\\nbranch refs/heads/feat/a\\n\\n'\n"
    "    printf 'worktree /repo.wt-d\\nHEAD abcdef1234567890\\n\\n'\n"
    "    return 0\n  fi\n}\n"
)

LIST = "\n".join(
    [
        "worktree  ブランチ\t\t\t",
        "repo  main\t/repo\trepo\tmain",
        "wt-a  feat/a\t/repo.wt-a\twt-a\tfeat/a",
        "wt-d  abcdef1\t/repo.wt-d\twt-d\tabcdef1",
    ]
)


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-f", "-c", f'source "{GIT_FILTER}"; export EXIT_CODE_SIGINT=130 COLUMNS=120\n{snippet}'],
        capture_output=True,
        text=True,
        env=sanitized_env(),
    )


def run_reload(gh_body):
    """reloadスクリプトをshで実行する。ghはPATH先頭のスタブに差し替える。"""
    script = run_zsh("_filter_worktree_pr_reload_script").stdout
    with tempfile.TemporaryDirectory() as tmp:
        gh = Path(tmp) / "gh"
        gh.write_text(f"#!/bin/sh\n{gh_body}\n")
        gh.chmod(0o755)
        env = sanitized_env({"PATH": f"{tmp}:/usr/bin:/bin", "_WT_PR_LIST": LIST})
        return subprocess.run(
            ["sh", "-c", 'eval "$_WT_PR_SCRIPT"'],
            capture_output=True,
            text=True,
            env={**env, "_WT_PR_SCRIPT": script},
        )


class WorktreePickerPrNumberTest(unittest.TestCase):
    def test_target_picker_passes_load_reload_bind(self):
        result = run_zsh(
            FAKE_FILTER_ECHO_ARGS + FAKE_GIT + "_filter_git_worktree_path --target-picker"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            'ARG:load:reload-sync(eval "$_WT_PR_SCRIPT")+unbind(load)', result.stderr
        )

    def test_non_target_picker_passes_load_reload_bind(self):
        result = run_zsh(FAKE_FILTER_ECHO_ARGS + FAKE_GIT + "_filter_git_worktree_path")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ARG:load:reload-sync(eval "$_WT_PR_SCRIPT")+unbind(load)', result.stderr)
        self.assertEqual(result.stdout.strip(), "/repo")

    def test_reload_appends_pr_number_to_matching_branch_only(self):
        result = run_reload(r"printf 'feat/a\t12\nother\t99\n'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "worktree  ブランチ\t\t\t",
                "repo  main\t/repo\trepo\tmain",
                "wt-a  #12 feat/a\t/repo.wt-a\twt-a\tfeat/a",
                "wt-d  abcdef1\t/repo.wt-d\twt-d\tabcdef1",
            ],
        )

    def test_reload_keeps_list_unchanged_when_gh_fails(self):
        result = run_reload("exit 1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), LIST.splitlines())

    def test_reload_keeps_list_unchanged_when_no_prs(self):
        result = run_reload("exit 0")
        self.assertEqual(result.stdout.splitlines(), LIST.splitlines())


if __name__ == "__main__":
    unittest.main()
