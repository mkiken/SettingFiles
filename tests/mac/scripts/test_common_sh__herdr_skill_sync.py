import os
import subprocess
import unittest
from pathlib import Path


from support import REPO_ROOT
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
SKILL_RELATIVE_PATH = "ai/common/skills/herdr/SKILL.md"


def run_zsh(script: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in ("FILTER_COMMAND", "FILTER_TOOL", "HERDR_ENV", "TMUX", "TMUX_PANE"):
        env.pop(name, None)
    env.update({"PATH": SYSTEM_PATH})
    env.update(env_overrides or {})

    return subprocess.run(
        ["/bin/zsh", "-fc", script],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class SyncHerdrSkillTest(unittest.TestCase):
    """sync_herdr_skill: repo 内 ai/common/skills/herdr/SKILL.md を upstream と同期する。

    ポリシー: 差分があれば repo ファイルを upstream で自動上書きするが、
    git add は絶対にしない(未ステージのまま残し、コミット判断は人間に委ねる)。
    取得失敗時は既存ファイルを保護し、update 全体は止めない(rc=0 で継続)。
    """

    def run_sync(
        self,
        *,
        upstream_content: str | None,
        curl_present: bool = True,
        curl_rc: int = 0,
        repo_skill_content: str = "original content\n",
        stage_in_git: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        import tempfile

        tmp_repo = Path(tempfile.mkdtemp(prefix="settingfiles-herdr-skill-sync-"))
        try:
            skill_path = tmp_repo / SKILL_RELATIVE_PATH
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(repo_skill_content, encoding="utf-8")

            common_sh = (REPO_ROOT / "mac/scripts/common.sh").read_text(encoding="utf-8")

            definitions = [common_sh]
            if curl_present:
                if upstream_content is None:
                    curl_body = f"return {curl_rc}"
                else:
                    # print -r -- は末尾に改行を1つ付与するため、期待値と揃えるために
                    # 呼び出し側が渡した文字列の末尾改行は先に取り除いておく。
                    escaped = upstream_content.rstrip("\n").replace("'", "'\\''")
                    curl_body = f"print -r -- '{escaped}'; return {curl_rc}"
                definitions.append(f"function curl() {{ {curl_body} }}")
            else:
                # command -v curl / curl 自体を「存在しない」ものとして扱わせる。
                # 実機の /usr/bin/curl が PATH 上に見えてしまうため、command を
                # オーバーライドして curl の存在確認を常に失敗させる。
                definitions.append(
                    "function command() { "
                    'if [[ "$1" == "-v" && "$2" == "curl" ]]; then return 1; fi; '
                    "builtin command \"$@\"; "
                    "}"
                )

            if stage_in_git:
                init_git = (
                    f"git -C {tmp_repo} init -q; "
                    f"git -C {tmp_repo} add -A; "
                    f"git -C {tmp_repo} -c user.email=t@t -c user.name=t commit -q -m init"
                )
            else:
                init_git = ""

            script = "; ".join(
                (
                    *definitions,
                    init_git,
                    f'sync_herdr_skill "{tmp_repo}"',
                    "print -r -- rc=$?",
                )
            )
            result = run_zsh(script)
            return result, skill_path
        finally:
            pass

    def tearDown_tmp(self, path: Path) -> None:
        import shutil

        shutil.rmtree(path.parents[3], ignore_errors=True)

    def test_matching_upstream_reports_up_to_date_and_leaves_file_untouched(self):
        content = "same content\n"
        result, skill_path = self.run_sync(upstream_content=content, repo_skill_content=content)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("up to date", result.stdout + result.stderr)
        self.assertEqual(skill_path.read_text(encoding="utf-8"), content)
        self.tearDown_tmp(skill_path)

    def test_differing_upstream_overwrites_repo_file_without_staging(self):
        upstream = "new upstream content\n"
        original = "stale local content\n"
        result, skill_path = self.run_sync(
            upstream_content=upstream,
            repo_skill_content=original,
            stage_in_git=True,
        )

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("UPDATED", result.stdout + result.stderr)
        self.assertEqual(skill_path.read_text(encoding="utf-8"), upstream)

        tmp_repo = skill_path.parents[3]
        status = subprocess.run(
            ["git", "-C", str(tmp_repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(SKILL_RELATIVE_PATH, status.stdout)

        staged = subprocess.run(
            ["git", "-C", str(tmp_repo), "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(staged.stdout.strip(), "", "sync_herdr_skill must never stage changes")
        self.tearDown_tmp(skill_path)

    def test_curl_failure_preserves_existing_file_and_does_not_fail_the_run(self):
        original = "kept as-is\n"
        result, skill_path = self.run_sync(upstream_content=None, curl_rc=1, repo_skill_content=original)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("Warning", result.stdout + result.stderr)
        self.assertEqual(skill_path.read_text(encoding="utf-8"), original)
        self.tearDown_tmp(skill_path)

    def test_missing_curl_command_preserves_existing_file_and_does_not_fail_the_run(self):
        original = "kept as-is\n"
        result, skill_path = self.run_sync(
            upstream_content=None, curl_present=False, repo_skill_content=original
        )

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("Warning", result.stdout + result.stderr)
        self.assertIn("curl", result.stdout + result.stderr)
        self.assertEqual(skill_path.read_text(encoding="utf-8"), original)
        self.tearDown_tmp(skill_path)

    def test_empty_upstream_response_is_treated_as_failure_and_file_is_preserved(self):
        original = "kept as-is\n"
        result, skill_path = self.run_sync(upstream_content="", repo_skill_content=original)

        self.assertEqual(result.stdout.splitlines()[-1], "rc=0")
        self.assertIn("Warning", result.stdout + result.stderr)
        self.assertEqual(skill_path.read_text(encoding="utf-8"), original)
        self.tearDown_tmp(skill_path)


class SyncHerdrSkillWiringTest(unittest.TestCase):
    """sync_herdr_skill が update フローに一度だけ、正しい順序で配線されていることを確認する。"""

    def read_text(self, path: str) -> str:
        return (REPO_ROOT / path).read_text(encoding="utf-8")

    def test_called_once_from_claude_update_before_setup_ai_skills(self):
        claude_update = self.read_text("mac/updates/claude.sh")

        self.assertEqual(claude_update.count("sync_herdr_skill"), 1)
        self.assertLess(
            claude_update.index("sync_herdr_skill"),
            claude_update.index("setup_ai_skills"),
        )

    def test_not_called_from_other_update_or_initialization_scripts(self):
        other_scripts = (
            "mac/updates/codex.sh",
            "mac/updates/gemini.sh",
            "mac/initialization/ai/claude.sh",
            "mac/initialization/ai/codex.sh",
            "mac/initialization/ai/gemini.sh",
        )
        for script_path in other_scripts:
            with self.subTest(script=script_path):
                self.assertNotIn("sync_herdr_skill", self.read_text(script_path))


if __name__ == "__main__":
    unittest.main()
