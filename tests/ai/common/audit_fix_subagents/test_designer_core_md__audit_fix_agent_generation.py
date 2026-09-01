import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
COMMON_SCRIPT = REPO_ROOT / "mac/scripts/common.sh"

ROLES = ("designer", "implementer")
MARKDOWN_PLATFORMS = ("claude", "gemini")


class AuditFixAgentGenerationTest(unittest.TestCase):
    """Runs the real generate_audit_fix_agents against a fixture tree.

    The fixture copies the real repository fragments into a tempdir and
    reassigns the sourced Repo global, so generation never touches the
    committed outputs.
    """

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.fixture_root = Path(temp_dir.name)

        common_dst = self.fixture_root / "ai/common/audit_fix_subagents"
        common_dst.mkdir(parents=True)
        for role in ROLES:
            shutil.copy(
                REPO_ROOT / f"ai/common/audit_fix_subagents/{role}_core.md",
                common_dst,
            )

        for platform in ("claude", "gemini", "codex"):
            src_dst = self.fixture_root / f"ai/{platform}/agents_src/audit_fix"
            src_dst.mkdir(parents=True)
            (self.fixture_root / f"ai/{platform}/agents").mkdir(parents=True)
            suffix = "toml" if platform == "codex" else "md"
            for role in ROLES:
                shutil.copy(
                    REPO_ROOT / f"ai/{platform}/agents_src/audit_fix/head_{role}.{suffix}",
                    src_dst,
                )

    def run_fn(self, fn: str) -> subprocess.CompletedProcess[str]:
        script = f'''
source "{COMMON_SCRIPT}"
Repo="{self.fixture_root}/"
{fn}
'''
        return subprocess.run(
            ["zsh", "-c", script, "audit-fix-agent-generation-test"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def markdown_path(self, platform: str, role: str) -> Path:
        return self.fixture_root / f"ai/{platform}/agents/audit-fix-{role}.md"

    def codex_path(self, role: str) -> Path:
        return self.fixture_root / f"ai/codex/agents/audit_fix_{role}.toml"

    def test_claude_agents_pin_a_model_per_role(self):
        result = self.run_fn("generate_audit_fix_agents claude")

        self.assertEqual(result.returncode, 0, result.stderr)
        # モデル分離がこの生成の目的そのもの。designer=賢い / implementer=安い が
        # frontmatter で固定されていることを確認する
        expected = {
            "designer": ("model: opus", "effort: high"),
            "implementer": ("model: sonnet", "effort: low"),
        }
        for role in ROLES:
            with self.subTest(role=role):
                out = self.markdown_path("claude", role)
                self.assertTrue(out.exists(), out)
                content = out.read_text(encoding="utf-8")
                self.assertIn(f"name: audit-fix-{role}", content)
                for token in expected[role]:
                    self.assertIn(token, content)

    def test_generated_notice_stays_inside_the_frontmatter(self):
        result = self.run_fn("generate_audit_fix_agents claude")

        self.assertEqual(result.returncode, 0, result.stderr)
        for role in ROLES:
            with self.subTest(role=role):
                lines = self.markdown_path("claude", role).read_text(
                    encoding="utf-8"
                ).splitlines()
                notice_index = next(
                    i
                    for i, line in enumerate(lines)
                    if line.startswith("# GENERATED FILE - do not edit.")
                )
                closing_index = next(
                    i for i, line in enumerate(lines[1:], start=1) if line == "---"
                )
                # frontmatter 内の YAML コメントなら実行時トークンを消費しない。
                # 本文先頭に漏れるとプロンプトとして課金される
                self.assertLess(notice_index, closing_index)

    def frontmatter(self, path: Path) -> str:
        # 本文には "replacement text" のような語が現れるため、tools の検査は
        # frontmatter に限定しないと誤判定する
        lines = path.read_text(encoding="utf-8").splitlines()
        closing = next(i for i, line in enumerate(lines[1:], start=1) if line == "---")
        return "\n".join(lines[1:closing])

    def test_gemini_agents_pin_a_model_and_the_tools_each_role_needs(self):
        result = self.run_fn("generate_audit_fix_agents gemini")

        self.assertEqual(result.returncode, 0, result.stderr)
        designer = self.frontmatter(self.markdown_path("gemini", "designer"))
        implementer = self.frontmatter(self.markdown_path("gemini", "implementer"))
        self.assertIn("model: gemini-2.5-pro", designer)
        self.assertIn("model: gemini-2.5-flash", implementer)
        # designer は設計ファイルを書くだけ、implementer は設定ファイルを編集する
        self.assertIn("write_file", designer)
        self.assertNotIn("replace", designer)
        self.assertIn("replace", implementer)

    def test_codex_agents_separate_roles_by_reasoning_effort(self):
        result = self.run_fn("generate_audit_fix_agents codex")

        self.assertEqual(result.returncode, 0, result.stderr)
        # Codex はリポジトリ内でモデル値が1種類しかないため effort が唯一の分離軸
        expected_effort = {"designer": "high", "implementer": "low"}
        for role in ROLES:
            with self.subTest(role=role):
                out = self.codex_path(role)
                self.assertTrue(out.exists(), out)
                content = out.read_text(encoding="utf-8")
                lines = content.splitlines()
                self.assertTrue(
                    lines[0].startswith("# GENERATED FILE - do not edit."), lines[0]
                )
                self.assertIn(f'name = "audit_fix_{role}"', content)
                self.assertIn('sandbox_mode = "danger-full-access"', content)
                self.assertIn(
                    f'model_reasoning_effort = "{expected_effort[role]}"', content
                )
                self.assertIn("developer_instructions = '''", content)
                self.assertEqual(lines[-1], "'''")

    def test_unknown_platform_is_rejected(self):
        result = self.run_fn("generate_audit_fix_agents bogus")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(
            "unknown platform 'bogus' for generate_audit_fix_agents", result.stderr
        )

    def test_generation_is_idempotent(self):
        result = self.run_fn("verify_audit_fix_agent_generation_idempotency")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Verified idempotent generation for 6 output(s).", result.stdout
        )

    def test_triple_quote_in_fragment_fails_codex_generation(self):
        core = self.fixture_root / "ai/common/audit_fix_subagents/designer_core.md"
        core.write_text(
            core.read_text(encoding="utf-8") + "\nbad ''' marker\n",
            encoding="utf-8",
        )

        result = self.run_fn("generate_audit_fix_agents codex")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("''' found in audit_fix_designer fragment", result.stderr)
        self.assertFalse(self.codex_path("designer").exists())

    def test_triple_quote_does_not_block_markdown_platforms(self):
        core = self.fixture_root / "ai/common/audit_fix_subagents/designer_core.md"
        core.write_text(
            core.read_text(encoding="utf-8") + "\nbad ''' marker\n",
            encoding="utf-8",
        )

        for platform in MARKDOWN_PLATFORMS:
            with self.subTest(platform=platform):
                result = self.run_fn(f"generate_audit_fix_agents {platform}")

                # ガードが Codex 限定なのは意図的: YAML には ''' の構文的意味がない。
                # 対称にすると理由なく Claude/Gemini の生成を壊す
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.markdown_path(platform, "designer").exists())


if __name__ == "__main__":
    unittest.main()
