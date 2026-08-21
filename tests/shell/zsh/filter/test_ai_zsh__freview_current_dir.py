import os
import subprocess
import unittest

from support import REPO_ROOT

from .test_ai_zsh__freview_worktree import (
    AI_ALIASES,
    AI_FILTER,
    GH_ALIASES,
    GIT_FILTER,
    GITHUB_FILTER,
    OTHER_ALIASES,
    ZSH,
    FreviewWorktreeFixture,
)


class FreviewCurrentDirDirtyStateTest(FreviewWorktreeFixture, unittest.TestCase):
    """freview -c（_fai-pr-review経由、現在地でレビューする経路）のdirty確認フロー。

    _fai-pr-reviewは`freview -c`だけでなくfcl-pr-review/fgm-pr-reviewからも共有される
    共通ヘルパーで、worktree経路とは異なりgit -Cではなく$PWD（=カレントディレクトリ）を
    対象に_freview_resolve_dirty_stateを呼ぶ。この経路単体のテストは従来存在しなかった
    （dirty checkがinlineだったため）。
    """

    def dirty_env(self, **overrides):
        env = {"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.repo)}
        env.update(overrides)
        return env

    def untracked_env(self, **overrides):
        env = {"FREVIEW_UNTRACKED": "1", "FREVIEW_DIRTY_PATH": str(self.repo)}
        env.update(overrides)
        return env

    def test_clean_never_prompts(self):
        # クリーンなら何も聞かない
        # （tests/shell/zsh/alias/ai/test_ai_review_launcher.pyのconfirm不在ピンと同種の不変条件）
        result, values = self.run_freview(args="-c")

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("DIRTY_PROMPT ")], [], calls)
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)

    def test_tracked_change_aborts_before_pr_picker(self):
        result, values = self.run_freview(args="-c", extra_env=self.dirty_env())

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("GH ")], [], calls)
        # repo/worktreeピッカーは呼ばれないため、PRピッカー到達前ならfilter呼び出しは0回
        self.assertEqual([c for c in calls if c == "FILTER_CALL"], [], calls)

    def test_untracked_only_reset_cleans_without_restore(self):
        # 未追跡のみのときはgit restoreを呼ばない（対象なしでの呼び出しは
        # pathspecエラーになるため）。worktree経路と同じ挙動をここでも固定する
        result, values = self.run_freview(
            args="-c",
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="reset"),
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("GIT_RESTORE ")], [], calls)
        self.assertEqual(len([c for c in calls if c.startswith("GIT_CLEAN ")]), 1, calls)
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)

    def test_dirty_check_targets_pwd_not_selected_worktree(self):
        # worktree経路とは対象が逆であることの証明。ここでは現在地(=self.repo)が
        # 対象になる（tests/shell/zsh/filter/test_ai_zsh__freview_worktree.pyの
        # test_dirty_check_targets_selected_worktree_not_cwdと対になる）
        result, values = self.run_freview(
            args="-c",
            extra_env={"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.worktree)},
        )

        # 現在地(repo)はdirty_pathと一致しないためcleanと判定され起動する
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        review_calls = [c for c in self.calls() if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, result.stderr)


class FreviewClPrReviewSharesDirtyCheckTest(FreviewWorktreeFixture, unittest.TestCase):
    """fcl-pr-review/fgm-pr-reviewは_fai-pr-review経由で同じdirty確認を共有する
    （決定事項4の副作用。fcl-pr-review自体はcl-pr-reviewを呼ぶだけの薄いラッパーのため、
    ここではcl-pr-reviewをstubして中断/到達だけを検証する）。
    """

    def run_fcl_pr_review(self, extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "SET": str(REPO_ROOT),
            "FREVIEW_REPO": str(self.repo),
            "FREVIEW_WORKTREE": str(self.worktree),
            "FREVIEW_LOG": str(self.log),
            "FREVIEW_PR_LINE": "42\tsome title\tauthor\tmain\tfeature",
            "HERDR_ENV": "1",
            "TMUX": "",
            **(extra_env or {}),
        }
        script = f'''
            source "{OTHER_ALIASES}"
            source "{GH_ALIASES}"
            source "{AI_ALIASES}"
            source "{GIT_FILTER}"
            source "{GITHUB_FILTER}"
            source "{AI_FILTER}"
            cl-pr-review() {{ printf 'CL_PR_REVIEW %s\\n' "$*" >> "$FREVIEW_LOG"; }}
            _freview_prompt_dirty_action() {{
                printf 'DIRTY_PROMPT %s\\n' "$*" >> "$FREVIEW_LOG"
                print -r -- "${{FREVIEW_DIRTY_ACTION:-abort}}"
            }}
            fcl-pr-review
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=env,
        )
        values = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__")
        }
        return result, values

    def test_dirty_repo_aborts_before_cl_pr_review(self):
        result, values = self.run_fcl_pr_review(
            extra_env={"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.repo)}
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("CL_PR_REVIEW")], [], self.calls())


if __name__ == "__main__":
    unittest.main()
