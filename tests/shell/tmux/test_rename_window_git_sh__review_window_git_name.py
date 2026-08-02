import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
AI_FILTER = REPO_ROOT / "shell/zsh/filter/ai.zsh"
ZSH = shutil.which("zsh")

GARBAGE_PWD = "GARBAGE_PWD_LINE"
GARBAGE_LS = "GARBAGE  LS  GRID"


def run_git_name(work_dir: Path, target: str) -> tuple[int, list[str], str]:
    """chpwdフック（ゴミをstdoutにprint）と-qを解さないcd関数上書き（zoxide相当）を
    登録した状態で_review_window_git_nameを実行し、
    (関数のexit code, 出力行リスト, スクリプトstderr) を返す。
    フックと上書きはスクリプト自身のcd後に定義するため、混入源は関数内のcdのみ。"""
    script = f'''
autoload -Uz add-zsh-hook
source "{AI_FILTER}" || exit 98
cd "{work_dir}" || exit 99
_test_chpwd_garbage() {{
    print -r -- "{GARBAGE_PWD}"
    print -r -- "{GARBAGE_LS}"
}}
add-zsh-hook chpwd _test_chpwd_garbage
cd() {{ print -r -- "CD_OVERRIDE_BROKEN"; return 1 }}
out=$(_review_window_git_name "{target}")
rc=$?
print -r -- "RC=${{rc}}"
print -r -- "OUTPUT_START"
print -r -- "${{out}}"
print -r -- "OUTPUT_END"
'''
    result = subprocess.run([ZSH, "-fc", script], capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"zsh script failed: rc={result.returncode} stderr={result.stderr}"
        )
    lines = result.stdout.splitlines()
    rc = int(next(l for l in lines if l.startswith("RC=")).removeprefix("RC="))
    start = lines.index("OUTPUT_START") + 1
    end = lines.index("OUTPUT_END")
    return rc, lines[start:end], result.stderr


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=testuser", "-c", "user.email=test@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def make_repo(parent: Path, name: str = "repo") -> Path:
    repo = parent / name
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("test\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "init")
    return repo


class ReviewWindowGitNameTest(unittest.TestCase):
    """_review_window_git_nameがchpwdフック出力に汚染されず正しい名前を返すこと。

    対話シェルではchpwdフック(_chpwd_ls_abbrev)がpwd+ls出力をstdoutへ出すため、
    関数内の素のcdだとコマンド置換にゴミが混入し、herdrタブラベルが
    フルパス+ls一覧の複数行になる実バグがあった（cd -qで抑制する）。
    """

    def assert_clean_single_line(self, rc: int, out_lines: list[str], expected: str):
        self.assertEqual(rc, 0)
        self.assertEqual(out_lines, [expected])
        joined = "\n".join(out_lines)
        self.assertNotIn(GARBAGE_PWD, joined)
        self.assertNotIn(GARBAGE_LS, joined)

    def test_chpwd_hook_output_is_not_captured(self):
        # 本命ガード: 非デフォルトブランチのgit repoで、フック出力が混入せず
        # "repo名/ブランチ末尾" の1行だけを返す
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = make_repo(Path(temp_dir))
            git(repo, "checkout", "-q", "-b", "feature/fix-tabs")

            rc, out_lines, _ = run_git_name(repo, str(repo))

            self.assert_clean_single_line(rc, out_lines, "repo/fix-tabs")

    def test_same_directory_target(self):
        # ai-all実経路: target == PWD（同一ディレクトリへのcdでもchpwdは発火する）
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = make_repo(Path(temp_dir))
            git(repo, "checkout", "-q", "-b", "feature/fix-tabs")

            rc, out_lines, _ = run_git_name(repo, "$PWD")

            self.assert_clean_single_line(rc, out_lines, "repo/fix-tabs")

    def test_non_git_directory_returns_basename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plain = Path(temp_dir) / "plain-dir"
            plain.mkdir()

            rc, out_lines, _ = run_git_name(plain, str(plain))

            self.assert_clean_single_line(rc, out_lines, "plain-dir")

    def test_default_branch_returns_repo_name_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = make_repo(Path(temp_dir))
            git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            git(repo, "symbolic-ref", "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main")

            rc, out_lines, _ = run_git_name(repo, str(repo))

            self.assert_clean_single_line(rc, out_lines, "repo")

    def test_branch_abbrev_length_boundary(self):
        # ブランチ末尾は20文字を超えたときのみ先頭20文字+…に短縮される
        cases = [
            ("20文字ちょうどは無変換", "a" * 20, "repo/" + "a" * 20),
            ("21文字は先頭20文字+…", "b" * 21, "repo/" + "b" * 20 + "…"),
        ]
        for desc, branch_tail, expected in cases:
            with self.subTest(desc):
                with tempfile.TemporaryDirectory() as temp_dir:
                    repo = make_repo(Path(temp_dir))
                    git(repo, "checkout", "-q", "-b", f"feature/{branch_tail}")

                    rc, out_lines, _ = run_git_name(repo, str(repo))

                    self.assert_clean_single_line(rc, out_lines, expected)


if __name__ == "__main__":
    unittest.main()
