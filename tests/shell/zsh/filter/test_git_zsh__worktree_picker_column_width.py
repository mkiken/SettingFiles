import subprocess
import unittest

from support import REPO_ROOT

GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"

# 候補行の中身を検証するため、stdinを読んでstderrへ吐くfake filterを使う
# (test_git_zsh__worktree_picker_label.pyのFAKE_FILTERはstdinを読まないため、
#  そちらの既存テストは変更しない)
FAKE_FILTER_ECHO_CANDIDATES = (
    'filter() {\n'
    '  local l\n'
    '  while IFS= read -r l; do print -r -- "CAND:$l" >&2; done\n'
    '  print -r -- $\'/repo\\t/repo\\trepo\\tmain\'\n'
    '}\n'
)

LONG_NAME = "eternal-server.task-if-mapping-sheet-name-20260817203026"


def fake_git_worktree_list(entries):
    """entriesは(worktree_path, branch_or_None)のリスト。Noneはdetached扱い(HEAD行のみ)。"""
    body = 'git() {\n  if [[ "$1 $2" == "worktree list" ]]; then\n'
    for path, branch in entries:
        if branch is None:
            body += f"    printf 'worktree {path}\\nHEAD abcdef1234567890\\n\\n'\n"
        else:
            body += f"    printf 'worktree {path}\\nbranch refs/heads/{branch}\\n\\n'\n"
    body += "    return 0\n  fi\n}\n"
    return body


def run_zsh(snippet, columns=None, extra_env_lines=""):
    env_prefix = "export EXIT_CODE_SIGINT=130\n"
    if columns is not None:
        env_prefix += f"export COLUMNS={columns}\n"
    else:
        env_prefix += "unset COLUMNS\n"
    env_prefix += extra_env_lines
    return subprocess.run(
        ["zsh", "-f", "-c", f'source "{GIT_FILTER}"; {env_prefix}{snippet}'],
        capture_output=True,
        text=True,
    )


class WorktreePickerColumnWidthTest(unittest.TestCase):
    """_filter_git_worktree_pathの列幅算出・中央省略ロジックを検証する。"""

    def _candidate_lines(self, result):
        return [
            line[len("CAND:"):]
            for line in result.stderr.splitlines()
            if line.startswith("CAND:")
        ]

    def test_a1_short_names_not_truncated_and_sized_to_actual_max(self):
        snippet = (
            FAKE_FILTER_ECHO_CANDIDATES
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", "feature")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=200)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._candidate_lines(result)
        self.assertEqual(len(lines), 3)  # header + 2候補
        for line in lines:
            self.assertNotIn("…", line)
        # 左列幅は実測最長("repo.wt-a"=9文字)に揃う。上限まで広げない。
        # 表示名は右詰めパディングされるため、文字列split(区切りの2スペース)は
        # パディング分の空白と誤って混同しうる。ブランチ列の開始インデックス
        # (パディング済み左列+区切り2文字)で幅を検証する
        display_fields = [line.split("\t")[0] for line in lines]
        branch_starts = {field.index("main") for field in display_fields if "main" in field}
        branch_starts |= {field.index("feature") for field in display_fields if "feature" in field}
        self.assertEqual(len(branch_starts), 1, f"branch start indices differ: {branch_starts}")
        (branch_start,) = branch_starts
        self.assertEqual(branch_start, len("repo.wt-a") + 2)

    def test_a2_long_name_does_not_push_out_branch_column(self):
        snippet = (
            FAKE_FILTER_ECHO_CANDIDATES
            + fake_git_worktree_list([("/repo", "main"), (f"/repo.{LONG_NAME}", "feature")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._candidate_lines(result)
        # 各候補行(header除く)のブランチ開始インデックスが揃う = 左列幅が一致
        left_widths = set()
        for line in lines[1:]:
            display_field = line.split("\t")[0]
            branch = "main" if "main" in display_field else "feature"
            left_widths.add(display_field.index(branch))
        self.assertEqual(len(left_widths), 1, f"left column widths differ: {left_widths}")
        (left_width,) = left_widths
        self.assertLess(left_width, len(f"repo.{LONG_NAME}"))

    def test_a3_long_name_is_middle_truncated(self):
        snippet = (
            FAKE_FILTER_ECHO_CANDIDATES
            + fake_git_worktree_list([("/repo", "main"), (f"/repo.{LONG_NAME}", "feature")])
            + "_filter_git_worktree_path"
        )
        # 35%上限では末尾10文字を確保するのにcolumns=120では幅不足のため160を使う
        result = run_zsh(snippet, columns=160)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._candidate_lines(result)
        long_line = [l for l in lines if "feature" in l][0]
        display_name = long_line.split("\t")[0].split("  ")[0]
        self.assertEqual(display_name.count("…"), 1)
        self.assertTrue(display_name.startswith("repo."))
        self.assertTrue(display_name.endswith(LONG_NAME[-10:]))

    def test_a5_japanese_worktree_name_no_corruption(self):
        ja_name = "機能ブランチ用ワークツリー長い名前です"
        snippet = (
            FAKE_FILTER_ECHO_CANDIDATES
            + fake_git_worktree_list([("/repo", "main"), (f"/repo.{ja_name}", "日本語ブランチ")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=100)
        self.assertEqual(result.returncode, 0, result.stderr)
        # stderr全体がUTF-8として妥当にデコードできる(不正バイト境界で切れていない)
        raw_stderr = result.stderr.encode(result.stderr.encoding if hasattr(result.stderr, "encoding") else "utf-8", errors="surrogateescape")
        raw_stderr.decode("utf-8", errors="strict")
        lines = self._candidate_lines(result)
        ja_line = [l for l in lines if "日本語ブランチ" in l][0]
        display_field = ja_line.split("\t")[0]
        self.assertIn("…", display_field)

    def test_a6_japanese_branch_name_not_truncated(self):
        ja_branch = "日本語のとても長いブランチ名前ですこれはブランチなので省略されない"
        snippet = (
            FAKE_FILTER_ECHO_CANDIDATES
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", ja_branch)])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=100)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._candidate_lines(result)
        ja_line = [l for l in lines if ja_branch in l][0]
        # ブランチ名は全文がそのまま含まれる(省略対象外)
        self.assertIn(ja_branch, ja_line)

    def test_a7_tiny_terminal_clamps_to_minimum(self):
        snippet = (
            FAKE_FILTER_ECHO_CANDIDATES
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", "feature")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._candidate_lines(result)
        self.assertEqual(len(lines), 3)
        for line in lines:
            display_field = line.split("\t")[0]
            name_part = display_field.split("  ")[0]
            self.assertGreater(len(name_part), 0)


class TerminalColumnsTest(unittest.TestCase):
    """_filter_terminal_columnsのフォールバック順序を検証する。"""

    def _run(self, columns=None, tput_body="echo 100"):
        snippet = (
            f'tput() {{ {tput_body}; }}\n'
            "_filter_terminal_columns"
        )
        return run_zsh(snippet, columns=columns)

    def test_b1_columns_env_used_when_positive(self):
        result = self._run(columns=150)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "150")

    def test_b2_falls_back_to_tput_when_columns_zero(self):
        result = self._run(columns=0, tput_body="echo 100")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "100")

    def test_b3_falls_back_to_80_when_tput_fails(self):
        result = self._run(columns=None, tput_body="return 1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "80")

    def test_b4_non_numeric_columns_does_not_crash(self):
        snippet = 'tput() { echo 100; }\nCOLUMNS=abc\n_filter_terminal_columns'
        result = subprocess.run(
            ["zsh", "-f", "-c", f'source "{GIT_FILTER}"; export EXIT_CODE_SIGINT=130\n{snippet}'],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "100")

    def test_b5_empty_tput_output_falls_back_to_80(self):
        result = self._run(columns=None, tput_body="printf ''")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "80")


class TruncateMiddleTest(unittest.TestCase):
    """_filter_truncate_middleを直接検証する。"""

    def _run(self, s, limit):
        snippet = f'_filter_truncate_middle {s!r} {limit}'
        return run_zsh(snippet)

    def test_c1_short_string_passthrough(self):
        result = self._run("short", 32)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "short\n")

    def test_c2_long_ascii_name_truncated_to_exact_width(self):
        result = self._run(LONG_NAME, 32)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout.strip("\n")
        self.assertIn("…", out)
        width_check_snippet = f'echo -n {out!r} | wc -m'
        # 表示幅の直接検証はzsh側の${(m)#}が必要なため、別プロセスで測る
        width_snippet = f's={out!r}; echo ${{(m)#s}}'
        width_result = run_zsh(width_snippet)
        self.assertEqual(width_result.stdout.strip(), "32")

    def test_c3_japanese_long_string_within_limit_and_valid_utf8(self):
        ja = "日本語のとても長いブランチ名前ですこれは省略されるはず"
        result = self._run(ja, 20)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout.strip("\n")
        out.encode("utf-8").decode("utf-8", errors="strict")
        width_snippet = f's={out!r}; echo ${{(m)#s}}'
        width_result = run_zsh(width_snippet)
        self.assertLessEqual(int(width_result.stdout.strip()), 20)

    def test_c5_exact_limit_width_not_truncated(self):
        s = "0123456789012345678901234567890X"  # 32文字, 表示幅32
        result = self._run(s, 32)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip("\n"), s)

    def test_c6_limit_plus_one_is_truncated(self):
        s = "0123456789012345678901234567890XY"  # 33文字
        result = self._run(s, 32)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout.strip("\n")
        self.assertIn("…", out)
        width_snippet = f's={out!r}; echo ${{(m)#s}}'
        width_result = run_zsh(width_snippet)
        self.assertEqual(width_result.stdout.strip(), "32")

    def test_c7_stdout_is_single_line_no_local_leak(self):
        # ループ内local再宣言はtypesetの値をstdoutに混入させる回帰テスト
        result = self._run(LONG_NAME, 20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)


class OutputContractNonRegressionTest(unittest.TestCase):
    """フィールド追加後もcut -f2相当の出力契約が壊れないことを検証する。"""

    def test_d1_non_target_picker_returns_full_path_only(self):
        snippet = (
            'filter() { print -r -- $\'shown  branch\\t/some/full/path\\trawname\\trawbranch\'; }\n'
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", "feature")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "/some/full/path")

    def test_d2_target_picker_ctrl_o_prefixes_action(self):
        snippet = (
            'filter() { printf \'ctrl-o\\n%s\\n\' $\'shown  branch\\t/some/full/path\\trawname\\trawbranch\'; }\n'
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", "feature")])
            + "_filter_git_worktree_path --target-picker"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ctrl-o\t/some/full/path")

    def test_d3_target_picker_enter_defaults_action(self):
        snippet = (
            'filter() { print -r -- $\'shown  branch\\t/some/full/path\\trawname\\trawbranch\'; }\n'
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", "feature")])
            + "_filter_git_worktree_path --target-picker"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "enter\t/some/full/path")

    def test_d4_path_with_space_is_preserved(self):
        snippet = (
            'filter() { print -r -- $\'shown  branch\\t/tmp/feature worktree\\trawname\\trawbranch\'; }\n'
            + fake_git_worktree_list([("/repo", "main"), ("/repo.wt-a", "feature")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "/tmp/feature worktree")

    def test_d5_single_worktree_skips_ui_without_target_picker(self):
        snippet = (
            'filter() { echo "UNEXPECTED_FILTER_CALL" >&2; exit 1; }\n'
            + fake_git_worktree_list([("/repo", "main")])
            + "_filter_git_worktree_path"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "/repo")
        self.assertNotIn("UNEXPECTED_FILTER_CALL", result.stderr)

    def test_d6_single_worktree_shows_ui_with_target_picker(self):
        snippet = (
            'filter() { printf \'ctrl-s\\n%s\\n\' $\'shown  branch\\t/repo\\trawname\\trawbranch\'; }\n'
            + fake_git_worktree_list([("/repo", "main")])
            + "_filter_git_worktree_path --target-picker"
        )
        result = run_zsh(snippet, columns=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ctrl-s\t/repo")

    def test_d7_zero_candidates_returns_sigint(self):
        snippet = (
            'git() { if [[ "$1 $2" == "worktree list" ]]; then return 0; fi }\n'
            "_filter_git_worktree_path"
        )
        result = run_zsh(snippet)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertIn("選択可能なworktreeがありません", result.stderr)


class FilterArgsTest(unittest.TestCase):
    """filter呼び出しの引数(プレビュー/プレビューウィンドウ/既存オプション)を検証する。"""

    FAKE_FILTER_ARGS = 'filter() { printf "FILTER_ARGS %s\\n" "$*" >&2; }\n'

    def test_e1_preview_includes_all_fields_and_git_log(self):
        snippet = (
            self.FAKE_FILTER_ARGS
            + fake_git_worktree_list([("/repo", "main")])
            + "_filter_git_worktree_path --target-picker"
        )
        result = run_zsh(snippet, columns=120)
        self.assertIn("{3}", result.stderr)
        self.assertIn("{4}", result.stderr)
        self.assertIn("{2}", result.stderr)
        self.assertIn("git -C {2} log", result.stderr)

    def test_e2_preview_window_is_explicit(self):
        snippet = (
            self.FAKE_FILTER_ARGS
            + fake_git_worktree_list([("/repo", "main")])
            + "_filter_git_worktree_path --target-picker"
        )
        result = run_zsh(snippet, columns=120)
        self.assertIn("--preview-window=right:50%:wrap", result.stderr)

    def test_e3_existing_options_unchanged(self):
        snippet = (
            self.FAKE_FILTER_ARGS
            + fake_git_worktree_list([("/repo", "main")])
            + "_filter_git_worktree_path --target-picker"
        )
        result = run_zsh(snippet, columns=120)
        self.assertIn("--delimiter", result.stderr)
        self.assertIn("--with-nth 1", result.stderr)
        self.assertIn("--header-lines 1", result.stderr)


if __name__ == "__main__":
    unittest.main()
