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
    """freviewのrepo→worktree→PR選択を検証する隔離済みfixture。

    - zoxide/git worktree listでリポジトリ・worktreeを1件ずつ返す
    - filterはヘッダ文字列(Number\tTitle...)の有無でPRピッカーかworktreeピッカーかを判別する
      （_filter_zoxide_git_worktree_pathとPRピッカーが同じ`filter`コマンドを叩くため）
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
        # （現在地はdirtyだが選択worktreeはcleanというケースを区別するため）
        self._write_executable(
            "git",
            "#!/bin/sh\n"
            "if [ \"$1\" = worktree ] && [ \"$2\" = list ]; then\n"
            "  printf 'worktree %s\\nbranch refs/heads/main\\n\\n' \"$FREVIEW_REPO\"\n"
            "  printf 'worktree %s\\nbranch refs/heads/feature\\n\\n' \"$FREVIEW_WORKTREE\"\n"
            "  exit 0\n"
            "fi\n"
            "target=\"$PWD\"\n"
            "if [ \"$1\" = -C ]; then\n"
            "  target=\"$2\"\n"
            "  shift 2\n"
            "fi\n"
            "if [ \"$1\" = diff-index ]; then\n"
            "  if [ \"${FREVIEW_DIRTY:-}\" = 1 ] && [ \"$target\" = \"${FREVIEW_DIRTY_PATH:-$target}\" ]; then\n"
            "    exit 1\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            # 未追跡ファイルはFREVIEW_UNTRACKED_COUNT件（既定1件）を返す。
            # 表示の打ち切り（先頭10件+残数）を検証するため件数を可変にしている
            "if [ \"$1\" = ls-files ]; then\n"
            "  if [ \"${FREVIEW_UNTRACKED:-}\" = 1 ] && [ \"$target\" = \"${FREVIEW_DIRTY_PATH:-$target}\" ]; then\n"
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
        # filter: --headerの文言でrepoピッカー/worktreeピッカー/PRピッカーを判別する。
        # worktreeピッカーはcdq経由でrepoへcdした状態で呼ばれるため($PWD==repo)、
        # PWDでは区別できず--headerの文言で見分ける必要がある。
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
            "  *worktree*)\n"
            "    [ \"${FREVIEW_WORKTREE_CANCEL:-}\" = 1 ] && exit 0\n"
            "    printf '%s\\n' \"$FREVIEW_WORKTREE\"\n"
            "    ;;\n"
            "  *)\n"
            "    [ \"${FREVIEW_REPO_CANCEL:-}\" = 1 ] && exit 0\n"
            "    printf '%s\\n' \"$FREVIEW_REPO\"\n"
            "    ;;\n"
            "esac\n",
        )
        # gh: co(checkout)呼び出しをログへ記録。pr listは_fgh_select_pr_number経由で
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
            "if [ \"$1\" = co ]; then\n"
            "  [ \"${FREVIEW_GH_CO_FAIL:-}\" = 1 ] && exit 1\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = pr ] && [ \"$2\" = list ]; then\n"
            "  printf '[]'\n"
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
            review() {{ printf 'REVIEW review %s (AI_REVIEW_CWD=%s)\\n' "$*" "$AI_REVIEW_CWD" >> "$FREVIEW_LOG"; }}
            review-subagents() {{ printf 'REVIEW review-subagents %s (AI_REVIEW_CWD=%s)\\n' "$*" "$AI_REVIEW_CWD" >> "$FREVIEW_LOG"; }}
            # confirmはutils.zshに実装があるが対話待ちになるため差し替える。
            # 呼び出し引数を記録し、FREVIEW_CONFIRM_ANSWERで応答を切り替える
            confirm() {{
                printf 'CONFIRM %s\\n' "$*" >> "$FREVIEW_LOG"
                [[ "${{FREVIEW_CONFIRM_ANSWER:-no}}" == yes ]]
            }}
            {command} {args}
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
            print -r -- "__AI_REVIEW_CWD=${{AI_REVIEW_CWD:-<unset>}}"
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
    """freview（デフォルト）: repo→worktree→PR選択後、選択worktreeでcheckoutしてreviewを起動する。"""

    def test_selects_repo_worktree_pr_then_launches_review(self):
        result, values = self.run_freview()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        # 現シェルのAI_REVIEW_CWDは残らない（コマンド前置のみで漏れない）
        self.assertEqual(values["__AI_REVIEW_CWD"], "<unset>", result.stderr)

        calls = self.calls()
        gh_co_calls = [c for c in calls if c.startswith("GH co ")]
        self.assertEqual(len(gh_co_calls), 1, calls)
        self.assertIn(f"(pwd={self.worktree})", gh_co_calls[0])
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)
        self.assertIn("42", review_calls[0])
        self.assertIn(f"AI_REVIEW_CWD={self.worktree}", review_calls[0])

    def test_freview_subagents_launches_review_subagents(self):
        result, values = self.run_freview(command="freview-subagents")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        calls = self.calls()
        self.assertEqual(len([c for c in calls if c.startswith("REVIEW review-subagents ")]), 1, calls)
        self.assertEqual(len([c for c in calls if c.startswith("REVIEW review ")]), 0, calls)

    def test_freview_prompts_are_labeled_review_without_subagents(self):
        # 3ピッカーすべてのpromptに"review"が付き、"subagents"は付かないことを確認する
        # （押し間違いに気づけるようにする対策のfreview側の固定）
        result, values = self.run_freview()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        filter_args = [c for c in calls if c.startswith("FILTER_ARGS ")]
        self.assertEqual(len(filter_args), 3, calls)
        for args in filter_args:
            self.assertIn("--prompt review ", args, calls)
            self.assertNotIn("subagents", args, calls)

    def test_freview_subagents_prompts_are_labeled_with_subagents(self):
        # freview-subagents実行時は3ピッカーすべてのpromptに"review-subagents"が付く
        result, values = self.run_freview(command="freview-subagents")

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        filter_args = [c for c in calls if c.startswith("FILTER_ARGS ")]
        self.assertEqual(len(filter_args), 3, calls)
        for args in filter_args:
            self.assertIn("--prompt review-subagents ", args, calls)

    def test_pr_picker_runs_with_selected_worktree_as_cwd(self):
        result, values = self.run_freview()

        self.assertEqual(result.returncode, 0, result.stderr)
        # gh pr list (via ghpl_branch) がPRピッカー内で選択worktreeのcwdで呼ばれること
        calls = self.calls()
        pr_list_calls = [c for c in calls if c.startswith("GH pr list")]
        self.assertEqual(len(pr_list_calls), 1, calls)
        self.assertIn(f"(pwd={self.worktree})", pr_list_calls[0])

    def test_dirty_tracked_change_aborts_before_pr_picker(self):
        result, values = self.run_freview(
            extra_env={"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.worktree)}
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("作業中のファイルがあります", result.stderr)
        calls = self.calls()
        self.assertEqual([c for c in calls if c.startswith("GH ")], [], calls)
        # filterはrepo picker + worktree pickerの2回のみ呼ばれ、PRピッカーは呼ばれない
        pr_filter_calls = [c for c in calls if c == "FILTER_CALL"]
        self.assertEqual(len(pr_filter_calls), 2, calls)

    def untracked_env(self, **overrides):
        env = {"FREVIEW_UNTRACKED": "1", "FREVIEW_DIRTY_PATH": str(self.worktree)}
        env.update(overrides)
        return env

    def test_dirty_untracked_only_aborts_when_confirm_declined(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_CONFIRM_ANSWER="no")
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertEqual(len([c for c in self.calls() if c.startswith("CONFIRM ")]), 1, self.calls())
        self.assertEqual([c for c in self.calls() if c.startswith("GH ")], [])
        # PRピッカーへ到達しない: filterはrepo + worktreeの2回のみ
        self.assertEqual(len([c for c in self.calls() if c == "FILTER_CALL"]), 2, self.calls())

    def test_dirty_untracked_only_proceeds_when_confirm_accepted(self):
        # 過去のAIレビューが残した一時ファイルでPR一覧に到達できなくなる不具合の回帰テスト
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_CONFIRM_ANSWER="yes")
        )

        self.assertEqual(values["__STATUS"], "0", result.stderr)
        review_calls = [c for c in self.calls() if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, self.calls())
        self.assertIn("42", review_calls[0])

    def test_dirty_tracked_change_never_asks_for_confirmation(self):
        # 追跡ファイルの変更はレビュー対象差分に混入しうるため続行を選ばせない
        result, values = self.run_freview(
            extra_env={
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
                "FREVIEW_CONFIRM_ANSWER": "yes",
            }
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("CONFIRM ")], [], self.calls())
        self.assertIn("作業中のファイルがあります", result.stderr)

    def test_untracked_file_names_are_shown(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_CONFIRM_ANSWER="no", FREVIEW_UNTRACKED_COUNT="2")
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("未追跡ファイルが 2 件あります", result.stderr)
        self.assertIn("untracked1.txt", result.stderr)
        self.assertIn("untracked2.txt", result.stderr)

    def test_untracked_listing_is_truncated_after_ten(self):
        result, values = self.run_freview(
            extra_env=self.untracked_env(FREVIEW_CONFIRM_ANSWER="no", FREVIEW_UNTRACKED_COUNT="12")
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("未追跡ファイルが 12 件あります", result.stderr)
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

    def test_worktree_picker_cancelled_returns_sigint(self):
        result, values = self.run_freview(extra_env={"FREVIEW_WORKTREE_CANCEL": "1"})

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("GH ")], [])

    def test_pr_picker_cancelled_returns_sigint(self):
        result, values = self.run_freview(extra_env={"FREVIEW_PR_CANCEL": "1"})

        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertEqual([c for c in self.calls() if c.startswith("GH co")], [])

    def test_gh_co_failure_aborts_before_review(self):
        result, values = self.run_freview(extra_env={"FREVIEW_GH_CO_FAIL": "1"})

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("gh co", result.stderr)
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


class FreviewPopupPauseTest(FreviewWorktreeFixture, unittest.TestCase):
    """Herdr popupはコマンド終了と同時に閉じるため、エラー終了時のみキー待ちを挟む。"""

    PAUSE_MARKER = "何かキーを押すと閉じます"

    def test_pauses_on_error_inside_popup(self):
        result, values = self.run_freview(
            extra_env={
                "HERDR_POPUP_WRAPPED": "1",
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.worktree),
            }
        )

        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn(self.PAUSE_MARKER, result.stderr)

    def test_does_not_pause_on_error_outside_popup(self):
        result, values = self.run_freview(
            extra_env={"FREVIEW_DIRTY": "1", "FREVIEW_DIRTY_PATH": str(self.worktree)}
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
        # -c は現在地(=repo)のdirty checkで中断する
        result, values = self.run_freview(
            args="-c",
            extra_env={
                "HERDR_POPUP_WRAPPED": "1",
                "FREVIEW_DIRTY": "1",
                "FREVIEW_DIRTY_PATH": str(self.repo),
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
        gh_co_calls = [c for c in calls if c.startswith("GH co ")]
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
        # worktreeモードなのでrepo picker + worktree pickerの2回filterが呼ばれる
        self.assertEqual(len([c for c in calls if c == "FILTER_CALL"]), 3, calls)  # +PR picker
        review_calls = [c for c in calls if c.startswith("REVIEW review ")]
        self.assertEqual(len(review_calls), 1, calls)
        self.assertIn("X -c", review_calls[0])


if __name__ == "__main__":
    unittest.main()
