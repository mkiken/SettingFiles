import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


SCRIPT = REPO_ROOT / "mac/scripts/ai/codex.sh"
DIMENSIONS = ("default", "conflict", "overlap", "patch", "ambiguity", "concise")


class CodexConfigAuditorAgentsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "repo/ai/codex/agents"
        self.source.mkdir(parents=True)
        self.destination = self.root / "home/.codex/agents"
        self.destination.mkdir(parents=True)
        for dimension in DIMENSIONS:
            name = f"config_auditor_{dimension}.toml"
            (self.source / name).write_bytes((REPO_ROOT / "ai/codex/agents" / name).read_bytes())

    def install(self):
        return subprocess.run(
            ["zsh", "-c", 'Repo="$4/"; source "$3"; Repo="$1/"; HOME="$2"; setup_codex_config_auditor_agents',
             "test", str(self.root / "repo"), str(self.root / "home"), str(SCRIPT), str(REPO_ROOT)],
            env=sanitized_env(), text=True, capture_output=True,
        )

    def test_managed_links_become_regular_files(self):
        for source in self.source.iterdir():
            (self.destination / source.name).symlink_to(source)
        self.assertEqual(self.install().returncode, 0)
        for source in self.source.iterdir():
            destination = self.destination / source.name
            self.assertFalse(destination.is_symlink())
            self.assertEqual(destination.read_bytes(), source.read_bytes())
            tomllib.loads(destination.read_text())

    def test_unchanged_file_stays_and_changed_source_syncs(self):
        self.assertEqual(self.install().returncode, 0)
        source = self.source / "config_auditor_default.toml"
        destination = self.destination / source.name
        before = destination.stat()
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(destination.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(destination.stat().st_ino, before.st_ino)
        source.write_text(source.read_text() + "\n# changed generation\n")
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_invalid_source_preserves_all_destinations(self):
        self.assertEqual(self.install().returncode, 0)
        before = {p.name: p.read_bytes() for p in self.destination.iterdir()}
        (self.source / "config_auditor_default.toml").write_text("name = 'changed'\n")
        (self.source / "config_auditor_concise.toml").write_text("invalid = [")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual({p.name: p.read_bytes() for p in self.destination.iterdir()}, before)

    def test_unexpected_destinations_are_preserved(self):
        destination = self.destination / "config_auditor_concise.toml"
        for kind in ("file", "link", "directory"):
            with self.subTest(kind=kind):
                if kind == "file":
                    destination.write_text("name = 'user-owned'\n")
                elif kind == "link":
                    destination.symlink_to(self.root / "missing.toml")
                else:
                    destination.mkdir()
                self.assertNotEqual(self.install().returncode, 0)
                self.assertEqual(len(list(self.destination.iterdir())), 1)
                if kind == "file":
                    self.assertEqual(destination.read_text(), "name = 'user-owned'\n")
                    destination.unlink()
                elif kind == "link":
                    self.assertTrue(destination.is_symlink())
                    destination.unlink()
                else:
                    self.assertTrue(destination.is_dir())
                    destination.rmdir()

    def test_entrypoint_loops_leave_other_agents_symlinked(self):
        for filename in ("mac/initialization/ai/codex.sh", "mac/updates/codex.sh"):
            with self.subTest(filename=filename):
                text = (REPO_ROOT / filename).read_text()
                start = text.index("agents_dest=~/.codex/agents")
                end = text.index("\n# 共有コアスキル", start)
                # Other families and user agents must keep their existing link placement.
                for source in (REPO_ROOT / "ai/codex/agents").glob("*.toml"):
                    (self.source / source.name).write_bytes(source.read_bytes())
                custom = self.destination / "spec-reviewer.toml"
                custom.write_text("name = 'custom'\n")
                result = subprocess.run(
                    ["zsh", "-c", 'Repo="$5/"; source "$3"; Repo="$1/"; HOME="$2"; '
                     'make_symlink() { ln -sf "$1" "$2"; }; eval "$4"', "test",
                     str(self.root / "repo"), str(self.root / "home"), str(SCRIPT), text[start:end], str(REPO_ROOT)],
                    env=sanitized_env(), text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                for source in self.source.glob("*.toml"):
                    self.assertEqual((self.destination / source.name).is_symlink(),
                                     not source.name.startswith("config_auditor_"))
                self.assertEqual(custom.read_text(), "name = 'custom'\n")
