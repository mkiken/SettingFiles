import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

AI_FILTER = REPO_ROOT / "shell/zsh/filter/ai.zsh"
GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
GITHUB_FILTER = REPO_ROOT / "shell/zsh/filter/github.zsh"
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"
OTHER_ALIASES = REPO_ROOT / "shell/zsh/alias/other.zsh"
GH_ALIASES = REPO_ROOT / "shell/zsh/alias/gh.zsh"
ZSH = shutil.which("zsh")


class FreviewWorktreeFixture:
    """freviewのrepo→PR選択とworktree自動決定を検証する隔離済みfixture。

    - zoxide/git worktree listでリポジトリ・PRのheadブランチ(feature)を持つworktreeを返す
      （FREVIEW_NO_PR_WORKTREE=1でheadを持つworktreeを無くし、一時worktree作成経路にする）
    - wt stubはswitch呼び出しを記録し、成功時は作成後のworktree一覧に一時worktreeを加える
    - filterはヘッダ文字列(Number\tTitle...)の有無でPRピッカーかrepoピッカーかを判別する
    - review/review-subagentsは実行せず、呼び出し引数と環境変数をログへ記録するstubにする
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        # macOSの/tmpは/private/tmpへのsymlinkで、サブプロセス側の$PWDは実パスで
        # 解決されるため、比較のずれを避けるためこちら側もresolve()しておく
        self.root = Path(self.temp_dir.name).resolve()
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.worktree = self.root / "feature-worktree"
        self.worktree.mkdir()
        # wt switch pr:<N> が作る一時worktree（FREVIEW_NO_PR_WORKTREE=1の経路で使う）
        self.new_worktree = self.root / "review-tmp-worktree"
        self.new_worktree.mkdir()
        self.log = self.root / "calls.log"
        self._write_fake_commands()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_executable(self, name: str, body: str):
        path = self.bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def _write_fake_commands(self):
        # zoxide: リポジトリ1件だけを候補として返す
        self._write_executable(
            "zoxide",
            "#!/bin/sh\n"
            "if [ \"$1\" = query ] && [ \"$2\" = --list ]; then\n"
            "  printf '%s\\n' \"$FREVIEW_REPO\"\n"
            "  exit 0\n"
            "fi\n"
            "exit 0\n",
        )
        # git: worktree list --porcelain はworktree1件、それ以外は実gitへ委譲。
        # dirty checkは `git -C <path> ...` 形式で呼ばれるため、-Cの対象パスが
        # FREVIEW_DIRTY_PATHと一致する場合のみ汚れ扱いにする
        # （現在地はdirtyだが選択worktreeはcleanというケースを区別するため）。
        # restore/cleanは実行せずログへ記録するだけにする（本物のgit破壊コマンドを
        # 絶対に実行しない安全ガード）。FREVIEW_STILL_DIRTY=1のときはrestore/clean成功後も
        # 再検査のdiff-index/ls-filesをdirtyのまま返す（クリーン化失敗の再検査を検証するため）
        self._write_executable(
            "git",
            "#!/bin/sh\n"
            "target=\"$PWD\"\n"
            "if [ \"$1\" = -C ]; then\n"
            "  target=\"$2\"\n"
            "  shift 2\n"
            "fi\n"
            # worktree一覧: repo本体 + PRのheadブランチ(feature)を持つworktree。
            # wt switch後（wt_doneマーカーあり）は一時worktreeも加わる
            "if [ \"$1\" = worktree ] && [ \"$2\" = list ]; then\n"
            "  printf 'worktree %s\\nbranch refs/heads/main\\n\\n' \"$FREVIEW_REPO\"\n"
            "  [ \"${FREVIEW_NO_PR_WORKTREE:-}\" = 1 ] || printf 'worktree %s\\nbranch refs/heads/feature\\n\\n' \"$FREVIEW_WORKTREE\"\n"
            "  [ -e \"$FREVIEW_LOG.wt_done\" ] && printf 'worktree %s\\nbranch refs/heads/%s\\n\\n' \"$FREVIEW_NEW_WORKTREE\" \"$FREVIEW_NEW_BRANCH\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = for-each-ref ]; then\n"
            "  printf '%s\\n' ${FREVIEW_EXISTING_BRANCHES:-main}\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = branch ] && [ \"$2\" = --show-current ]; then\n"
            "  printf '%s\\n' \"$FREVIEW_NEW_BRANCH\"\n"
            "  exit 0\n"
            "fi\n"
            "is_dirty_target() {\n"
            "  [ \"$target\" = \"${FREVIEW_DIRTY_PATH:-$target}\" ]\n"
            "}\n"
            # reset実行済みかどうかをマーカーファイルで状態遷移させる。
            # FREVIEW_STILL_DIRTY=1のときだけマーカーを作らず、reset後も
            # dirtyのまま返す（クリーン化失敗の再検査を検証するため）
            "reset_done_marker=\"$FREVIEW_LOG.reset_done\"\n"
            "if [ \"$1\" = restore ]; then\n"
            "  printf 'GIT_RESTORE %s (path=%s)\\n' \"$*\" \"$target\" >> \"$FREVIEW_LOG\"\n"
            "  [ \"${FREVIEW_RESTORE_FAIL:-}\" = 1 ] && exit 1\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = clean ]; then\n"
            "  printf 'GIT_CLEAN %s (path=%s)\\n' \"$*\" \"$target\" >> \"$FREVIEW_LOG\"\n"
            "  [ \"${FREVIEW_CLEAN_FAIL:-}\" = 1 ] && exit 1\n"
            "  [ \"${FREVIEW_STILL_DIRTY:-}\" != 1 ] && : > \"$reset_done_marker\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = diff-index ] && [ \"$2\" = --name-only ]; then\n"
            "  if [ \"${FREVIEW_DIRTY:-}\" = 1 ] && is_dirty_target && [ ! -e \"$reset_done_marker\" ]; then\n"
            "    i=1\n"
            "    while [ \"$i\" -le \"${FREVIEW_DIRTY_COUNT:-1}\" ]; do\n"
            "      printf 'changed%s.txt\\n' \"$i\"\n"
            "      i=$((i + 1))\n"
            "    done\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = diff-index ]; then\n"
            "  if is_dirty_target && [ \"${FREVIEW_DIRTY:-}\" = 1 ] && [ ! -e \"$reset_done_marker\" ]; then\n"
            "    exit 1\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            # 未追跡ファイルはFREVIEW_UNTRACKED_COUNT件（既定1件）を返す。
            # 表示の打ち切り（先頭10件+残数）を検証するため件数を可変にしている
            "if [ \"$1\" = ls-files ]; then\n"
            "  if is_dirty_target && [ \"${FREVIEW_UNTRACKED:-}\" = 1 ] && [ ! -e \"$reset_done_marker\" ]; then\n"
            "    i=1\n"
            "    while [ \"$i\" -le \"${FREVIEW_UNTRACKED_COUNT:-1}\" ]; do\n"
            "      printf 'untracked%s.txt\\n' \"$i\"\n"
            "      i=$((i + 1))\n"
            "    done\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "exec /usr/bin/git \"$@\"\n",
        )
        # filter: --headerの文言でrepoピッカー/PRピッカーを判別する。
        # どちらもrepoへcdした状態で呼ばれうるため、PWDでは区別できない。
        # --label-prefix由来の--promptは判別に使わず、argv全体をログへ記録するだけにする
        # （headerの文言を変えると判別ロジックが壊れるため、prompt側だけで検証する）
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "printf 'FILTER_CALL\\n' >> \"$FREVIEW_LOG\"\n"
            "printf 'FILTER_ARGS %s\\n' \"$*\" >> \"$FREVIEW_LOG\"\n"
            "args=\"$*\"\n"
            "case \"$args\" in\n"
            "  *Number*)\n"
            "    [ \"${FREVIEW_PR_CANCEL:-}\" = 1 ] && exit 0\n"
            "    printf '%s\\n' \"$FREVIEW_PR_LINE\"\n"
            "    ;;\n"
            "  *)\n"
            "    [ \"${FREVIEW_REPO_CANCEL:-}\" = 1 ] && exit 0\n"
            "    printf '%s\\n' \"$FREVIEW_REPO\"\n"
            "    ;;\n"
            "esac\n",
        )
        # wt: switch呼び出しを記録。成功時は一時worktree作成済みマーカーを立てる
        # （FREVIEW_WT_NOOP=1なら立てない=wtが何も作らなかった場合）
        self._write_executable(
            "wt",
            "#!/bin/sh\n"
            "printf 'WT %s (pwd=%s)\\n' \"$*\" \"$PWD\" >> \"$FREVIEW_LOG\"\n"
            "[ \"${FREVIEW_WT_FAIL:-}\" = 1 ] && exit 1\n"
            "[ \"${FREVIEW_WT_NOOP:-}\" = 1 ] || : > \"$FREVIEW_LOG.wt_done\"\n"
            "exit 0\n",
        )
        # gh: pr checkout呼び出しをログへ記録。pr listは_fgh_select_pr_number経由で
        # 呼ばれる想定だがghpl_branchはgh.zshの実装をそのまま使うため、実PR取得は発生しない
        # （filterがヘッダで直接PR行を返すため、gh pr list自体は結果を捨てるだけでよい）。
        # gh.zshのトップレベルで実行される`gh config set editor nvim`はテストの関心事
        # ではないためログに残さない
        self._write_executable(
            "gh",
            "#!/bin/sh\n"
            "if [ \"$1\" = config ]; then\n"
            "  exit 0\n"
            "fi\n"
            "printf 'GH %s (pwd=%s)\\n' \"$*\" \"$PWD\" >> \"$FREVIEW_LOG\"\n"
            "if [ \"$1\" = pr ] && [ \"$2\" = checkout ]; then\n"
            "  [ \"${FREVIEW_GH_CO_FAIL:-}\" = 1 ] && exit 1\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = pr ] && [ \"$2\" = list ]; then\n"
            "  printf '[]'\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = pr ] && [ \"$2\" = view ]; then\n"
            "  [ \"${FREVIEW_GH_AUTHOR_FAIL:-}\" = 1 ] && exit 1\n"
            "  printf '%s\\n' \"${FREVIEW_PR_AUTHOR:-someone-else}\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = api ] && [ \"$2\" = user ]; then\n"
            "  printf '%s\\n' \"${FREVIEW_ME:-me}\"\n"
            "  exit 0\n"
            "fi\n"
            "exit 0\n",
        )

    def run_freview(self, command="freview", args="", extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "SET": str(REPO_ROOT),
            "FREVIEW_REPO": str(self.repo),
            "FREVIEW_WORKTREE": str(self.worktree),
            "FREVIEW_NEW_WORKTREE": str(self.new_worktree),
            "FREVIEW_NEW_BRANCH": "feature",
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
            _filter_zoxide_git_repo() {{
                local label_prefix=""
                if [[ "${{1:-}}" == "--label-prefix" ]]; then
                    label_prefix="$2"
                fi
                zoxide query --list | filter --height 40% --prompt "${{label_prefix:+$label_prefix }}repo> "
            }}
            review() {{ printf 'REVIEW review %s (AI_REVIEW_CWD=%s) [TEMP_WORKTREE=%s TEMP_BRANCH=%s]\\n' "$*" "$AI_REVIEW_CWD" "$AI_REVIEW_TEMP_WORKTREE" "$AI_REVIEW_TEMP_BRANCH" >> "$FREVIEW_LOG"; }}
            review-mx() {{ printf 'REVIEW review-mx %s (AI_REVIEW_CWD=%s) [TEMP_WORKTREE=%s TEMP_BRANCH=%s]\\n' "$*" "$AI_REVIEW_CWD" "$AI_REVIEW_TEMP_WORKTREE" "$AI_REVIEW_TEMP_BRANCH" >> "$FREVIEW_LOG"; }}
            review-subagents() {{ printf 'REVIEW review-subagents %s (AI_REVIEW_CWD=%s) [TEMP_WORKTREE=%s TEMP_BRANCH=%s]\\n' "$*" "$AI_REVIEW_CWD" "$AI_REVIEW_TEMP_WORKTREE" "$AI_REVIEW_TEMP_BRANCH" >> "$FREVIEW_LOG"; }}
            self-review() {{ printf 'REVIEW self-review %s (AI_REVIEW_CWD=%s) [TEMP_WORKTREE=%s TEMP_BRANCH=%s]\\n' "$*" "$AI_REVIEW_CWD" "$AI_REVIEW_TEMP_WORKTREE" "$AI_REVIEW_TEMP_BRANCH" >> "$FREVIEW_LOG"; }}
            self-review-mx() {{ printf 'REVIEW self-review-mx %s (AI_REVIEW_CWD=%s) [TEMP_WORKTREE=%s TEMP_BRANCH=%s]\\n' "$*" "$AI_REVIEW_CWD" "$AI_REVIEW_TEMP_WORKTREE" "$AI_REVIEW_TEMP_BRANCH" >> "$FREVIEW_LOG"; }}
            self-review-subagents() {{ printf 'REVIEW self-review-subagents %s (AI_REVIEW_CWD=%s) [TEMP_WORKTREE=%s TEMP_BRANCH=%s]\\n' "$*" "$AI_REVIEW_CWD" "$AI_REVIEW_TEMP_WORKTREE" "$AI_REVIEW_TEMP_BRANCH" >> "$FREVIEW_LOG"; }}
            # confirmはutils.zshに実装があるが対話待ちになるため差し替える。
            # 呼び出し引数を記録し、FREVIEW_CONFIRM_ANSWERで応答を切り替える。
            # dirty confirmは_freview_prompt_dirty_actionへ移行済みで、誤って
            # confirmが呼ばれた場合にログへ残って気づけるよう残置している
            confirm() {{
                printf 'CONFIRM %s\\n' "$*" >> "$FREVIEW_LOG"
                [[ "${{FREVIEW_CONFIRM_ANSWER:-no}}" == yes ]]
            }}
            # _freview_prompt_dirty_actionは対話待ちのread -kを含むため差し替える。
            # 呼び出し引数(allow_proceed)を記録し、FREVIEW_DIRTY_ACTIONで応答を切り替える
            _freview_prompt_dirty_action() {{
                printf 'DIRTY_PROMPT %s\\n' "$*" >> "$FREVIEW_LOG"
                print -r -- "${{FREVIEW_DIRTY_ACTION:-abort}}"
            }}
            {command} {args}
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
            print -r -- "__AI_REVIEW_CWD=${{AI_REVIEW_CWD:-<unset>}}"
            print -r -- "__AI_REVIEW_TEMP_WORKTREE=${{AI_REVIEW_TEMP_WORKTREE:-<unset>}}"
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

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


class FreviewWorktreeModeTest(FreviewWorktreeFixture, unittest.TestCase):
    """freview（デフォルト）: repo→PR選択後、PRのheadブランチを持つworktreeでcheckoutしてreviewを起動する。"""

    def test_reuses_existing_worktree_of_pr_head_then_launches_review(self):
        result, values = self.run_freview()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        # 現シェルのAI_REVIEW_CWDは残らない（コマンド前置のみで漏れない）
        self.assertEqual(values["__AI_REVIEW_CWD"], "<unset>", result.stderr)

        calls = self.calls()
        gh_co_calls = [c for c in calls if c.startswith("GH pr checkout ")]
        self.assertEqual(len(gh_co_calls), 1, calls)
        self.assertIn(f"(pwd={self.worktree})", gh_co_calls[0])
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)
        self.assertIn("42", review_calls[0])
        self.assertIn(f"AI_REVIEW_CWD={self.worktree}", review_calls[0])
        # 既存worktreeを使う経路では一時worktreeを作らず、削除対象も記録しない
        self.assertEqual([c for c in calls if c.startswith("WT ")], [], calls)
        self.assertIn("[TEMP_WORKTREE= TEMP_BRANCH=]", review_calls[0])

    def test_freview_mx_launches_review_mx_and_labels_the_pickers(self):
        result, values = self.run_freview(command="freview-mx")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        self.assertEqual(len([c for c in calls if c.startswith("REVIEW review-mx ")]), 1, calls)
        self.assertEqual(len([c for c in calls if c.startswith("REVIEW review ")]), 0, calls)
        # 軽量版との押し間違いに気づけるよう、2ピッカー(repo/PR)すべてのpromptに"review-mx"が付く
        filter_args = [c for c in calls if c.startswith("FILTER_ARGS ")]
        self.assertEqual(len(filter_args), 2, calls)
        for args in filter_args:
            self.assertIn("--prompt review-mx ", args, calls)

    def test_freview_subagents_launches_review_subagents(self):
        result, values = self.run_freview(command="freview-subagents")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        self.assertEqual(len([c for c in calls if c.startswith("REVIEW review-subagents ")]), 1, calls)
        self.assertEqual(len([c for c in calls if c.startswith("REVIEW review ")]), 0, calls)

    def test_freview_prompts_are_labeled_review_without_subagents(self):
        # 2ピッカー(repo/PR)すべてのpromptに"review"が付き、"subagents"は付かないことを確認する
        # （押し間違いに気づけるようにする対策のfreview側の固定）
        result, values = self.run_freview()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        filter_args = [c for c in calls if c.startswith("FILTER_ARGS ")]
        self.assertEqual(len(filter_args), 2, calls)
        for args in filter_args:
            self.assertIn("--prompt review ", args, calls)
            self.assertNotIn("subagents", args, calls)

    def test_freview_subagents_prompts_are_labeled_with_subagents(self):
        # freview-subagents実行時は2ピッカー(repo/PR)すべてのpromptに"review-subagents"が付く
        result, values = self.run_freview(command="freview-subagents")

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        filter_args = [c for c in calls if c.startswith("FILTER_ARGS ")]
        self.assertEqual(len(filter_args), 2, calls)
        for args in filter_args:
            self.assertIn("--prompt review-subagents ", args, calls)

    def review_calls(self, name):
        return [c for c in self.calls() if c.startswith(f"REVIEW {name} ")]

    def test_own_pr_launches_self_review_instead_of_review(self):
        result, _ = self.run_freview(extra_env={"FREVIEW_PR_AUTHOR": "me", "FREVIEW_ME": "me"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self_calls = self.review_calls("self-review")
        self.assertEqual(len(self_calls), 1, self.calls())
        self.assertIn("42", self_calls[0])
        self.assertIn(f"AI_REVIEW_CWD={self.worktree}", self_calls[0])
        self.assertEqual(self.review_calls("review"), [], self.calls())
        self.assertFalse([c for c in self.calls() if c.startswith("CONFIRM ")], self.calls())

    def test_others_pr_launches_review_without_confirm(self):
        result, _ = self.run_freview(extra_env={"FREVIEW_PR_AUTHOR": "someone-else", "FREVIEW_ME": "me"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.review_calls("review")), 1, self.calls())
        self.assertEqual(self.review_calls("self-review"), [], self.calls())
        self.assertFalse([c for c in self.calls() if c.startswith("CONFIRM ")], self.calls())

    def test_own_pr_with_subagents_launches_self_review_subagents(self):
        result, _ = self.run_freview(
            command="freview-subagents", extra_env={"FREVIEW_PR_AUTHOR": "me", "FREVIEW_ME": "me"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.review_calls("self-review-subagents")), 1, self.calls())
        self.assertEqual(self.review_calls("review-subagents"), [], self.calls())

    def test_own_pr_with_mx_launches_self_review_mx(self):
        result, _ = self.run_freview(
            command="freview-mx", extra_env={"FREVIEW_PR_AUTHOR": "me", "FREVIEW_ME": "me"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.review_calls("self-review-mx")), 1, self.calls())
        self.assertEqual(self.review_calls("review-mx"), [], self.calls())

    def test_own_pr_keeps_no_merge_before_pr_number(self):
        result, _ = self.run_freview(
            args="--no-merge", extra_env={"FREVIEW_PR_AUTHOR": "me", "FREVIEW_ME": "me"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self_calls = self.review_calls("self-review")
        self.assertEqual(len(self_calls), 1, self.calls())
        self.assertIn("self-review --no-merge 42 ", self_calls[0])

    def test_author_lookup_failure_confirms_and_yes_launches_self_review(self):
        result, _ = self.run_freview(
            extra_env={"FREVIEW_GH_AUTHOR_FAIL": "1", "FREVIEW_CONFIRM_ANSWER": "yes"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([c for c in self.calls() if c.startswith("CONFIRM ")]), 1, self.calls())
        self.assertEqual(len(self.review_calls("self-review")), 1, self.calls())
        self.assertEqual(self.review_calls("review"), [], self.calls())

    def test_author_lookup_failure_confirms_and_no_launches_review(self):
        result, _ = self.run_freview(
            extra_env={"FREVIEW_GH_AUTHOR_FAIL": "1", "FREVIEW_CONFIRM_ANSWER": "no"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([c for c in self.calls() if c.startswith("CONFIRM ")]), 1, self.calls())
        self.assertEqual(len(self.review_calls("review")), 1, self.calls())
        self.assertEqual(self.review_calls("self-review"), [], self.calls())

    def test_pr_picker_runs_with_selected_repo_as_cwd(self):
        result, values = self.run_freview()

        self.assertEqual(result.returncode, 0, result.stderr)
        # gh pr list (via ghpl_branch) がPRピッカー内で選択リポジトリのcwdで呼ばれること
        calls = self.calls()
        pr_list_calls = [c for c in calls if c.startswith("GH pr list")]
        self.assertEqual(len(pr_list_calls), 1, calls)
        self.assertIn(f"(pwd={self.repo})", pr_list_calls[0])

    def dirty_env(self, **overrides):
        env = {"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.worktree)}
        env.update(overrides)
        return env

    def untracked_env(self, **overrides):
        env = {"FREVIEW_UNTRACKED": "1", "FREVIEW_DIRTY_PATH": str(self.worktree)}
        env.update(overrides)
        return env

    def test_dirty_tracked_change_aborts_before_checkout(self):
        # dirty確認はPR選択後（headブランチを持つworktreeが決まってから）に行い、
        # 中止ならcheckoutもレビュー起動もしない
        result, values = self.run_freview(extra_env=self.dirty_env())

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertIn("がクリーンではありません", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("GH pr checkout")], [], calls)
        self.assertEqual([c for c in calls if c.startswith("REVIEW ")], [], calls)
        self.assertEqual(len([c for c in calls if c == "FILTER_CALL"]), 2, calls)

    def test_dirty_tracked_change_does_not_offer_proceed(self):
        # 追跡ファイルの変更はレビュー対象差分に混入しうるため続行を選択肢に出さない
        # （決定事項3の負のピン。allow_proceed=0がプロンプトへ渡ることを固定する）
        result, values = self.run_freview(
            extra_env=self.dirty_env(FREVIEW_DIRTY_ACTION="abort")
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        prompt_calls = [c for c in self.calls() if c.startswith("DIRTY_PROMPT ")]
        self.assertEqual(prompt_calls, ["DIRTY_PROMPT 0"], self.calls())

    def test_dirty_tracked_change_reset_restores_and_cleans(self):
        result, values = self.run_freview(
            extra_env=self.dirty_env(FREVIEW_DIRTY_ACTION="reset")
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        restore_calls = [c for c in calls if c.startswith("GIT_RESTORE ")]
        clean_calls = [c for c in calls if c.startswith("GIT_CLEAN ")]
        self.assertEqual(len(restore_calls), 1, calls)
        self.assertEqual(len(clean_calls), 1, calls)
        # restore→cleanの順で実行される
        self.assertLess(calls.index(restore_calls[0]), calls.index(clean_calls[0]), calls)
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)

    def test_reset_restore_includes_staged_and_worktree(self):
        # ステージ済み変更の取り残し防止の回帰ピン
        result, values = self.run_freview(
            extra_env=self.dirty_env(FREVIEW_DIRTY_ACTION="reset")
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        restore_calls = [c for c in self.calls() if c.startswith("GIT_RESTORE ")]
        self.assertEqual(len(restore_calls), 1, self.calls())
        self.assertIn("--staged", restore_calls[0])
        self.assertIn("--worktree", restore_calls[0])

    def test_reset_clean_does_not_pass_dash_x(self):
        # .gitignore済みファイルを消さない設計の負のピン
        # （理由: -xを付けると.env等の破壊的削除になるため意図的に付けない）
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="reset")
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        clean_calls = [c for c in self.calls() if c.startswith("GIT_CLEAN ")]
        self.assertEqual(len(clean_calls), 1, self.calls())
        self.assertNotIn("-x", clean_calls[0])

    def test_dirty_untracked_only_aborts_when_action_is_abort(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="abort")
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual(len([c for c in self.calls() if c.startswith("DIRTY_PROMPT ")]), 1, self.calls())
        self.assertEqual([c for c in self.calls() if c.startswith("GH pr checkout")], [])
        self.assertEqual([c for c in self.calls() if c.startswith("REVIEW ")], [])

    def test_dirty_untracked_only_proceeds_when_action_is_proceed(self):
        # 過去のAIレビューが残した一時ファイルでPR一覧に到達できなくなる不具合の回帰テスト
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="proceed")
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        review_calls = [c for c in self.calls() if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, self.calls())
        self.assertIn("42", review_calls[0])

    def test_dirty_untracked_only_offers_proceed(self):
        # 未追跡のみのときはallow_proceed=1がプロンプトへ渡る
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="abort")
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        prompt_calls = [c for c in self.calls() if c.startswith("DIRTY_PROMPT ")]
        self.assertEqual(prompt_calls, ["DIRTY_PROMPT 1"], self.calls())

    def test_dirty_untracked_only_reset_cleans_without_restore(self):
        # 未追跡のみのときはgit restoreを呼ばない: 対象(追跡変更)が無い状態で
        # restoreを呼ぶと「pathspec ':/' did not match any file(s)」で失敗するため
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="reset")
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("GIT_RESTORE ")], [], calls)
        self.assertEqual(len([c for c in calls if c.startswith("GIT_CLEAN ")]), 1, calls)

    def test_both_dirty_shows_both_listings_in_single_prompt(self):
        result, values = self.run_freview(
            extra_env={
                "FREVIEW_DIRTY": "1",
                "FREVIEW_UNTRACKED": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
                "FREVIEW_DIRTY_ACTION": "reset",
            }
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertIn("変更(1件):", result.stderr)
        self.assertIn("未追跡(1件):", result.stderr)
        calls = self.calls()
        self.assertEqual(len([c for c in calls if c.startswith("DIRTY_PROMPT ")]), 1, calls)
        self.assertEqual(len([c for c in calls if c.startswith("GIT_RESTORE ")]), 1, calls)
        self.assertEqual(len([c for c in calls if c.startswith("GIT_CLEAN ")]), 1, calls)

    def test_both_dirty_abort_skips_restore_and_clean(self):
        result, values = self.run_freview(
            extra_env={
                "FREVIEW_DIRTY": "1",
                "FREVIEW_UNTRACKED": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
                "FREVIEW_DIRTY_ACTION": "abort",
            }
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("GIT_RESTORE ")], [], calls)
        self.assertEqual([c for c in calls if c.startswith("GIT_CLEAN ")], [], calls)

    def test_reset_fails_when_still_dirty_after_cleanup(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="reset", FREVIEW_STILL_DIRTY="1")
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("未追跡ファイルが残っています", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("REVIEW ")], [], self.calls())

    def test_reset_fails_when_restore_fails(self):
        result, values = self.run_freview(
            extra_env=self.dirty_env(FREVIEW_DIRTY_ACTION="reset", FREVIEW_RESTORE_FAIL="1")
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        calls = self.calls()
        self.assertEqual(len([c for c in calls if c.startswith("GIT_RESTORE ")]), 1, calls)
        # restoreが失敗した場合はcleanを実行しない（部分的破壊を避ける）
        self.assertEqual([c for c in calls if c.startswith("GIT_CLEAN ")], [], calls)
        self.assertEqual([c for c in calls if c.startswith("REVIEW ")], [], calls)

    def test_reset_fails_when_clean_fails(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="reset", FREVIEW_CLEAN_FAIL="1")
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("削除できませんでした", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("REVIEW ")], [], self.calls())

    def test_changed_file_listing_is_truncated_after_ten(self):
        result, values = self.run_freview(
            extra_env=self.dirty_env(FREVIEW_DIRTY_ACTION="abort", FREVIEW_DIRTY_COUNT="12")
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertIn("変更(12件):", result.stderr)
        self.assertIn("changed10.txt", result.stderr)
        self.assertNotIn("changed11.txt", result.stderr)
        self.assertIn("他 2 件", result.stderr)

    def test_untracked_file_names_are_shown(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="abort", FREVIEW_UNTRACKED_COUNT="2")
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertIn("未追跡(2件):", result.stderr)
        self.assertIn("untracked1.txt", result.stderr)
        self.assertIn("untracked2.txt", result.stderr)

    def test_untracked_listing_is_truncated_after_ten(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_DIRTY_ACTION="abort", FREVIEW_UNTRACKED_COUNT="12")
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertIn("未追跡(12件):", result.stderr)
        self.assertIn("untracked10.txt", result.stderr)
        self.assertNotIn("untracked11.txt", result.stderr)
        self.assertIn("他 2 件", result.stderr)

    def test_dirty_check_targets_selected_worktree_not_cwd(self):
        # 現在地(リポジトリ本体)が汚れていても、選択worktreeがcleanなら正常に起動する
        # （git -C <選択worktree> で判定していることの証明）
        result, values = self.run_freview(
            extra_env={"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.repo)}
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        review_calls = [c for c in self.calls() if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, result.stderr)

    def test_repo_picker_cancelled_returns_sigint(self):
        result, values = self.run_freview(extra_env={"FREVIEW_REPO_CANCEL": "1"})

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("GH ")], [])

    def test_pr_picker_cancelled_returns_sigint(self):
        result, values = self.run_freview(extra_env={"FREVIEW_PR_CANCEL": "1"})

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("GH pr checkout")], [])

    def test_gh_co_failure_aborts_before_review(self):
        result, values = self.run_freview(extra_env={"FREVIEW_GH_CO_FAIL": "1"})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("gh pr checkout", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("REVIEW ")], [])

    def test_rejects_in_tmux_without_herdr(self):
        result, values = self.run_freview(extra_env={"HERDR_ENV": "", "TMUX": "test-client"})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("Herdr内で実行してください", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_rejects_outside_any_multiplexer(self):
        result, values = self.run_freview(extra_env={"HERDR_ENV": "", "TMUX": ""})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_no_merge_is_repositioned_before_pr_number(self):
        # _review_runは[--no-merge] [pr] [prompt...]の順を前提とするため、
        # 自前解決したPR番号の前に--no-mergeを再配置する必要がある
        result, values = self.run_freview(args="--no-merge '観点X'")

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        review_calls = [c for c in self.calls() if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, review_calls)
        self.assertIn("--no-merge 42 観点X", review_calls[0])


class FreviewTempWorktreeTest(FreviewWorktreeFixture, unittest.TestCase):
    """PRのheadブランチを持つworktreeが無いとき、レビュー用の一時worktreeを `wt switch pr:<N>` で作る。"""

    def run_temp(self, **kwargs):
        extra_env = {"FREVIEW_NO_PR_WORKTREE": "1", **kwargs.pop("extra_env", {})}
        return self.run_freview(extra_env=extra_env, **kwargs)

    def review_call(self, name="review"):
        calls = [c for c in self.calls() if c.startswith(f"REVIEW {name} ")]
        self.assertEqual(len(calls), 1, self.calls())
        return calls[0]

    def test_creates_temp_worktree_and_reviews_there(self):
        result, values = self.run_temp()

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        wt_calls = [c for c in calls if c.startswith("WT ")]
        self.assertEqual(len(wt_calls), 1, calls)
        self.assertEqual(wt_calls[0], f"WT switch pr:42 --no-cd (pwd={self.repo})")
        # wt switch pr:<N> がPRをcheckout済みで作るため、gh pr checkoutは不要
        self.assertEqual([c for c in calls if c.startswith("GH pr checkout")], [], calls)
        review = self.review_call()
        self.assertIn(f"AI_REVIEW_CWD={self.new_worktree})", review)
        # headブランチは作成前に存在しなかったので「このフローで新規作成」として記録する
        self.assertIn(f"[TEMP_WORKTREE={self.new_worktree} TEMP_BRANCH=feature]", review)

    def test_preexisting_local_branch_is_not_recorded_as_new(self):
        # 作成前から存在したローカルブランチはユーザー資産。削除対象にしない
        result, values = self.run_temp(extra_env={"FREVIEW_EXISTING_BRANCHES": "main feature"})

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertIn(f"[TEMP_WORKTREE={self.new_worktree} TEMP_BRANCH=]", self.review_call())

    def test_own_pr_launches_self_review_with_temp_worktree(self):
        result, values = self.run_temp(extra_env={"FREVIEW_PR_AUTHOR": "me", "FREVIEW_ME": "me"})

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertIn(f"TEMP_WORKTREE={self.new_worktree} ", self.review_call("self-review"))

    def test_temp_worktree_env_does_not_leak_into_calling_shell(self):
        result, values = self.run_temp()

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(values["__AI_REVIEW_TEMP_WORKTREE"], "<unset>", result.stderr)

    def test_skips_dirty_check_for_fresh_worktree(self):
        # 作ったばかりのworktreeは確認不要。汚れ扱いにしてもプロンプトは出ない
        result, values = self.run_temp(
            extra_env={"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.new_worktree)}
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("DIRTY_PROMPT")], [], self.calls())

    def test_wt_failure_aborts_without_launching_review(self):
        result, values = self.run_temp(extra_env={"FREVIEW_WT_FAIL": "1"})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("wt switch pr:42 に失敗しました", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("REVIEW ")], [], self.calls())

    def test_no_new_worktree_aborts_because_nothing_safe_to_delete(self):
        # wtが既存worktreeへ切り替えただけ等で新規worktreeを特定できないときは、
        # 削除対象を決められないためレビューを起動しない
        result, values = self.run_temp(extra_env={"FREVIEW_WT_NOOP": "1"})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("一時worktreeを特定できませんでした", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("REVIEW ")], [], self.calls())

    def test_pr_cancel_does_not_create_worktree(self):
        result, values = self.run_temp(extra_env={"FREVIEW_PR_CANCEL": "1"})

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("WT ")], [], self.calls())


class FreviewPopupPauseTest(FreviewWorktreeFixture, unittest.TestCase):
    """Herdr popupはコマンド終了と同時に閉じるため、エラー終了時のみキー待ちを挟む。"""

    PAUSE_MARKER = "何かキーを押すと閉じます"

    def test_pauses_on_error_inside_popup(self):
        # dirty confirmでabortを選んだ場合はユーザーの正常操作(130)なのでpauseしない。
        # ここではreset失敗という真のエラー(1)でpauseすることを検証する
        result, values = self.run_freview(
            extra_env={
                "HERDR_POPUP_WRAPPED": "1",
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
                "FREVIEW_DIRTY_ACTION": "reset",
                "FREVIEW_RESTORE_FAIL": "1",
            }
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn(self.PAUSE_MARKER, result.stderr)

    def test_does_not_pause_on_dirty_abort(self):
        # 中止はユーザーの正常操作(130)なのでpopup内でもpauseしない
        result, values = self.run_freview(
            extra_env={
                "HERDR_POPUP_WRAPPED": "1",
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
            }
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertNotIn(self.PAUSE_MARKER, result.stderr)

    def test_does_not_pause_on_error_outside_popup(self):
        result, values = self.run_freview(
            extra_env={
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
                "FREVIEW_DIRTY_ACTION": "reset",
                "FREVIEW_RESTORE_FAIL": "1",
            }
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertNotIn(self.PAUSE_MARKER, result.stderr)

    def test_does_not_pause_on_picker_cancel(self):
        # キャンセルは正常操作。待たせるとpopupを閉じるのに余計な操作が要る
        result, values = self.run_freview(
            extra_env={"HERDR_POPUP_WRAPPED": "1", "FREVIEW_PR_CANCEL": "1"}
        )

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertNotIn(self.PAUSE_MARKER, result.stderr)

    def test_does_not_pause_on_success(self):
        result, values = self.run_freview(extra_env={"HERDR_POPUP_WRAPPED": "1"})

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertNotIn(self.PAUSE_MARKER, result.stderr)

    def test_pauses_on_error_in_current_mode(self):
        # -c 経路のエラーもディスパッチャで拾う（pauseを1箇所へ集約していることの固定）。
        # -c は現在地(=repo)のdirty checkで中断する。abortは130（正常操作）なので
        # ここでもreset失敗という真のエラーでpauseを検証する
        result, values = self.run_freview(
            args="-c",
            extra_env={
                "HERDR_POPUP_WRAPPED": "1",
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.repo),
                "FREVIEW_DIRTY_ACTION": "reset",
                "FREVIEW_RESTORE_FAIL": "1",
            },
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn(self.PAUSE_MARKER, result.stderr)

    def test_pause_writes_mark_when_provided(self):
        # マークは「pauseした事実の記録」であってpopup判定ではない、という不変条件を固定する
        with tempfile.NamedTemporaryFile() as mark:
            result, values = self.run_freview(
                extra_env={
                    "HERDR_POPUP_WRAPPED": "1",
                    "HERDR_POPUP_PAUSE_MARK": mark.name,
                    "FREVIEW_DIRTY": "1",
                    "FREVIEW_DIRTY_PATH": str(self.worktree),
                    "FREVIEW_DIRTY_ACTION": "reset",
                    "FREVIEW_RESTORE_FAIL": "1",
                }
            )

            self.assertEqual(values["__STATUS"], "1", result.stderr)
            self.assertIn(self.PAUSE_MARKER, result.stderr)
            self.assertTrue(Path(mark.name).stat().st_size > 0)

    def test_mark_stays_empty_when_not_wrapped(self):
        with tempfile.NamedTemporaryFile() as mark:
            result, values = self.run_freview(
                extra_env={
                    "HERDR_POPUP_PAUSE_MARK": mark.name,
                    "FREVIEW_DIRTY": "1",
                    "FREVIEW_DIRTY_PATH": str(self.worktree),
                    "FREVIEW_DIRTY_ACTION": "reset",
                    "FREVIEW_RESTORE_FAIL": "1",
                }
            )

            self.assertEqual(values["__STATUS"], "1", result.stderr)
            self.assertNotIn(self.PAUSE_MARKER, result.stderr)
            self.assertEqual(Path(mark.name).stat().st_size, 0)

    def test_mark_stays_empty_on_picker_cancel(self):
        with tempfile.NamedTemporaryFile() as mark:
            result, values = self.run_freview(
                extra_env={
                    "HERDR_POPUP_WRAPPED": "1",
                    "HERDR_POPUP_PAUSE_MARK": mark.name,
                    "FREVIEW_PR_CANCEL": "1",
                }
            )

            self.assertEqual(values["__STATUS"], "130", result.stderr)
            self.assertEqual(Path(mark.name).stat().st_size, 0)


class FreviewCurrentModeTest(FreviewWorktreeFixture, unittest.TestCase):
    """freview -c: 従来動作（現在地でPR選択→checkout→review）。"""

    def test_dash_c_skips_worktree_picker_and_uses_current_location(self):
        result, values = self.run_freview(args="-c")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        # repo/worktreeピッカーは呼ばれない: filterはPRピッカー(Numberヘッダ)の1回のみ
        self.assertEqual(len([c for c in calls if c == "FILTER_CALL"]), 1, calls)
        gh_co_calls = [c for c in calls if c.startswith("GH pr checkout ")]
        self.assertEqual(len(gh_co_calls), 1, calls)
        self.assertIn(f"(pwd={self.repo})", gh_co_calls[0])
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)
        # -cではAI_REVIEW_CWDを設定しないため、review内では未設定(空文字)のまま
        self.assertIn("AI_REVIEW_CWD=)", review_calls[0])

    def test_dash_c_forwards_extra_args_after_stripping_flag(self):
        result, values = self.run_freview(args="-c --no-merge '観点X'")

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)
        self.assertIn("--no-merge", review_calls[0])
        self.assertIn("観点X", review_calls[0])

    def test_dash_c_only_recognised_at_head(self):
        # 先頭以外の-cはreviewへの引数としてそのまま残り、worktreeモードで動く
        result, values = self.run_freview(args="X -c")

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        # worktreeモードなのでrepo picker + PR pickerの2回filterが呼ばれる
        self.assertEqual(len([c for c in calls if c == "FILTER_CALL"]), 2, calls)
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)
        self.assertIn("X -c", review_calls[0])


if __name__ == "__main__":
    unittest.main()
