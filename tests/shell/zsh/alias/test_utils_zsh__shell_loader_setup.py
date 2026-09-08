import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT


def run_zsh(script: str, home: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["zsh", "-fc", script],
        cwd=REPO_ROOT,
        env={
            "HOME": str(home),
            "SET": f"{REPO_ROOT}/",
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        text=True,
        capture_output=True,
        check=False,
    )


class ShellLoaderSetupTest(unittest.TestCase):
    def test_loader_preserves_tool_appended_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            zshrc = home / ".zshrc"
            managed = REPO_ROOT / "shell/zsh/managed.zsh"
            bun_block = "\n".join(
                (
                    "# bun completions",
                    '[ -s "/Users/testuser/.bun/_bun" ] && source "/Users/testuser/.bun/_bun"',
                    "",
                    "# bun",
                    'export BUN_INSTALL="$HOME/.bun"',
                    'export PATH="$BUN_INSTALL/bin:$PATH"',
                    "",
                )
            )
            zshrc.write_text(bun_block, encoding="utf-8")

            script = (
                "source shell/zsh/alias/utils.zsh; "
                f"ensure_settingfiles_shell_loader {zshrc} {managed} zsh; "
                f"ensure_settingfiles_shell_loader {zshrc} {managed} zsh"
            )
            result = run_zsh(script, home)

            self.assertEqual(result.returncode, 0, result.stderr)
            content = zshrc.read_text(encoding="utf-8")
            self.assertEqual(content.count("# >>> SettingFiles managed zsh >>>"), 1)
            self.assertEqual(content.count("# <<< SettingFiles managed zsh <<<"), 1)
            self.assertLess(
                content.index("# >>> SettingFiles managed zsh >>>"),
                content.index("# bun completions"),
            )
            self.assertIn(f'source "{managed}"', content)
            self.assertIn(bun_block.strip(), content)

    def test_loader_replaces_existing_managed_block_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            zshrc = home / ".zshrc"
            managed = REPO_ROOT / "shell/zsh/managed.zsh"
            zshrc.write_text(
                "\n".join(
                    (
                        "# before",
                        "# >>> SettingFiles managed zsh >>>",
                        'source "/old/managed.zsh"',
                        "# <<< SettingFiles managed zsh <<<",
                        "# after",
                        "",
                    )
                ),
                encoding="utf-8",
            )

            result = run_zsh(
                f"source shell/zsh/alias/utils.zsh; ensure_settingfiles_shell_loader {zshrc} {managed} zsh",
                home,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = zshrc.read_text(encoding="utf-8")
            self.assertEqual(content.count("# >>> SettingFiles managed zsh >>>"), 1)
            self.assertNotIn("/old/managed.zsh", content)
            self.assertIn("# before", content)
            self.assertIn("# after", content)

    def test_loader_converts_symlink_without_copying_managed_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            zshrc = home / ".zshrc"
            target = home / "repo-managed.zsh"
            managed = REPO_ROOT / "shell/zsh/managed.zsh"
            target.write_text("# old managed content\n", encoding="utf-8")
            zshrc.symlink_to(target)

            result = run_zsh(
                f"source shell/zsh/alias/utils.zsh; ensure_settingfiles_shell_loader {zshrc} {managed} zsh",
                home,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(zshrc.is_symlink())
            content = zshrc.read_text(encoding="utf-8")
            self.assertIn(f'source "{managed}"', content)
            self.assertNotIn("# old managed content", content)

    def test_loader_label_defaults_to_zsh_when_omitted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            zshrc = home / ".zshrc"
            managed = REPO_ROOT / "shell/zsh/managed.zsh"

            result = run_zsh(
                f"source shell/zsh/alias/utils.zsh; ensure_settingfiles_shell_loader {zshrc} {managed}",
                home,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = zshrc.read_text(encoding="utf-8")
            self.assertIn("# >>> SettingFiles managed zsh >>>", content)
            self.assertIn("# <<< SettingFiles managed zsh <<<", content)

    def test_loader_uses_bash_label_for_bash_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            bash_profile = home / ".bash_profile"
            managed = REPO_ROOT / "shell/bash/managed.bash"

            result = run_zsh(
                f"source shell/zsh/alias/utils.zsh; "
                f"ensure_settingfiles_shell_loader {bash_profile} {managed} bash",
                home,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = bash_profile.read_text(encoding="utf-8")
            self.assertIn("# >>> SettingFiles managed bash >>>", content)
            self.assertIn("# <<< SettingFiles managed bash <<<", content)
            self.assertIn(f'source "{managed}"', content)

    def test_loader_zsh_and_bash_blocks_coexist_independently(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            zshrc = home / ".zshrc"
            bash_profile = home / ".bash_profile"
            managed_zsh = REPO_ROOT / "shell/zsh/managed.zsh"
            managed_bash = REPO_ROOT / "shell/bash/managed.bash"

            script = (
                "source shell/zsh/alias/utils.zsh; "
                f"ensure_settingfiles_shell_loader {zshrc} {managed_zsh} zsh; "
                f"ensure_settingfiles_shell_loader {bash_profile} {managed_bash} bash; "
                # zsh 側の再実行が bash 側ブロックへ影響しないことを確認する
                f"ensure_settingfiles_shell_loader {zshrc} {managed_zsh} zsh"
            )
            result = run_zsh(script, home)

            self.assertEqual(result.returncode, 0, result.stderr)
            zsh_content = zshrc.read_text(encoding="utf-8")
            bash_content = bash_profile.read_text(encoding="utf-8")
            self.assertEqual(zsh_content.count("# >>> SettingFiles managed zsh >>>"), 1)
            self.assertEqual(bash_content.count("# >>> SettingFiles managed bash >>>"), 1)
            self.assertNotIn("managed bash", zsh_content)
            self.assertNotIn("managed zsh", bash_content)

    def test_loader_bash_label_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            bash_profile = home / ".bash_profile"
            managed = REPO_ROOT / "shell/bash/managed.bash"

            script = (
                "source shell/zsh/alias/utils.zsh; "
                f"ensure_settingfiles_shell_loader {bash_profile} {managed} bash; "
                f"ensure_settingfiles_shell_loader {bash_profile} {managed} bash"
            )
            result = run_zsh(script, home)

            self.assertEqual(result.returncode, 0, result.stderr)
            content = bash_profile.read_text(encoding="utf-8")
            self.assertEqual(content.count("# >>> SettingFiles managed bash >>>"), 1)
            self.assertEqual(content.count("# <<< SettingFiles managed bash <<<"), 1)

    def test_loader_converts_bash_profile_symlink_without_copying_managed_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            bash_profile = home / ".bash_profile"
            target = home / "repo-managed.bash"
            managed = REPO_ROOT / "shell/bash/managed.bash"
            target.write_text("# old managed content\n", encoding="utf-8")
            bash_profile.symlink_to(target)

            result = run_zsh(
                f"source shell/zsh/alias/utils.zsh; "
                f"ensure_settingfiles_shell_loader {bash_profile} {managed} bash",
                home,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(bash_profile.is_symlink())
            content = bash_profile.read_text(encoding="utf-8")
            self.assertIn(f'source "{managed}"', content)
            self.assertNotIn("# old managed content", content)


if __name__ == "__main__":
    unittest.main()
