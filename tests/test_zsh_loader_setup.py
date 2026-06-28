import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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


class ZshLoaderSetupTest(unittest.TestCase):
    def test_loader_preserves_tool_appended_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            zshrc = home / ".zshrc"
            managed = REPO_ROOT / "shell/zsh/managed.zsh"
            bun_block = "\n".join(
                (
                    "# bun completions",
                    '[ -s "/Users/morikensuke/.bun/_bun" ] && source "/Users/morikensuke/.bun/_bun"',
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
                f"ensure_settingfiles_zsh_loader {zshrc} {managed}; "
                f"ensure_settingfiles_zsh_loader {zshrc} {managed}"
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
                f"source shell/zsh/alias/utils.zsh; ensure_settingfiles_zsh_loader {zshrc} {managed}",
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
                f"source shell/zsh/alias/utils.zsh; ensure_settingfiles_zsh_loader {zshrc} {managed}",
                home,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(zshrc.is_symlink())
            content = zshrc.read_text(encoding="utf-8")
            self.assertIn(f'source "{managed}"', content)
            self.assertNotIn("# old managed content", content)


if __name__ == "__main__":
    unittest.main()
