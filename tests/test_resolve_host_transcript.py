import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_resolve(args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """resolve_host_transcript を bash から source して呼び出す。

    args は関数名以降の引数列（例: '"sid" "/tmp/cfg"'）。
    """
    script = (
        f'source "{REPO_ROOT}/shell/tmux/ai_notification_summary.sh"; '
        f"resolve_host_transcript {args}"
    )
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, env=env
    )


def make_transcript(config_dir: str, project: str, sid: str, mtime: float | None = None) -> str:
    """config_dir/projects/<project>/<sid>.jsonl を作成し、絶対パスを返す。"""
    proj_dir = Path(config_dir) / "projects" / project
    proj_dir.mkdir(parents=True, exist_ok=True)
    path = proj_dir / f"{sid}.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return str(path)


class ResolveHostTranscriptTest(unittest.TestCase):
    SID = "7d5eb184-df66-4473-88bc-f344aa9077f8"

    def test_valid_sid_returns_matching_transcript(self):
        """#1 有効sid・単一プロジェクト: そのパスを返し exit 0。"""
        with tempfile.TemporaryDirectory() as cfg:
            expected = make_transcript(cfg, "p1", self.SID)
            result = run_resolve(f'"{self.SID}" "{cfg}"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), expected)

    def test_multiple_projects_returns_newest(self):
        """#2 同sidが2プロジェクトに存在: 最新mtimeのものを返す。"""
        with tempfile.TemporaryDirectory() as cfg:
            make_transcript(cfg, "p_old", self.SID, mtime=1_000_000_000)
            newer = make_transcript(cfg, "p_new", self.SID, mtime=2_000_000_000)
            result = run_resolve(f'"{self.SID}" "{cfg}"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), newer)

    def test_nonexistent_sid_fails(self):
        """#3 一致するjsonlが無い: 空出力・exit 非0。"""
        with tempfile.TemporaryDirectory() as cfg:
            make_transcript(cfg, "p1", self.SID)
            result = run_resolve(f'"does-not-exist" "{cfg}"')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")

    def test_empty_sid_fails(self):
        """#4 空文字列 sid: 空出力・exit 非0（globワイルドカードを走らせない）。"""
        with tempfile.TemporaryDirectory() as cfg:
            result = run_resolve(f'"" "{cfg}"')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")

    def test_default_sid_fails(self):
        """#5 "default" sid: 空出力・exit 非0。"""
        with tempfile.TemporaryDirectory() as cfg:
            result = run_resolve(f'"default" "{cfg}"')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")

    def test_resolves_from_explicit_config_dir_arg(self):
        """#6 CLAUDE_CONFIG_DIR ではなく第2引数のdirから解決する。"""
        with tempfile.TemporaryDirectory() as cfg, tempfile.TemporaryDirectory() as other:
            expected = make_transcript(cfg, "p1", self.SID)
            # CLAUDE_CONFIG_DIR は別ディレクトリを指すが、第2引数が優先されること
            result = run_resolve(
                f'"{self.SID}" "{cfg}"', env_extra={"CLAUDE_CONFIG_DIR": other}
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), expected)


if __name__ == "__main__":
    unittest.main()
