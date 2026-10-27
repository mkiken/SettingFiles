import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from support import REPO_ROOT, sanitized_env


SCRIPT = REPO_ROOT / "mac/scripts/ai/codex.sh"


class CodexContextModeSetupTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.cache = self.base / "codex/plugins/cache/context-mode/context-mode/1.0"
        self.cache.mkdir(parents=True)
        self.record = self.base / "calls"
        self.env = sanitized_env({
            "CODEX_HOME": str(self.base / "codex"),
            "PATH": f"{self.bin}:{os.defpath}:/opt/homebrew/bin:/usr/local/bin",
            "HOME": str(self.base),
        })
        self.stub("codex", 'print(\'{"installed":[{"pluginId":"context-mode@context-mode","version":"1.0"}]}\')')
        self.stub("npm", '''
from pathlib import Path
import sys
p = Path('.npmrc')
content = p.read_text() if p.exists() else ''
if sys.argv[2] == 'get':
    print('false' if 'bin-links=false' in content else 'true')
else:
    p.write_text(content + '\\nbin-links=false\\n')
''')
        self.stub("trash", '''
from pathlib import Path
import sys
Path(sys.argv[1]).unlink()
''')

    def stub(self, name, body):
        executable = self.bin / name
        executable.write_text("#!/usr/bin/env python3\n" + body + "\n")
        executable.chmod(0o755)

    def run_function(self, function="repair_codex_context_mode_cache", prelude=""):
        script = f'Repo={shlex.quote(str(REPO_ROOT) + "/")}\nsource {shlex.quote(str(SCRIPT))}\n{prelude}\n{function}'
        return subprocess.run(["zsh", "-fc", script], env=self.env,
                              capture_output=True, text=True, cwd=self.base)

    def bin_link(self, nested=False):
        module = self.cache / "node_modules"
        if nested:
            module /= "tsx/node_modules"
        directory = module / ".bin"
        directory.mkdir(parents=True, exist_ok=True)
        target = module / "tool.js"
        target.write_text("library content")
        link = directory / "tool"
        link.symlink_to(target)
        return link, target

    def test_removes_only_bin_links_preserves_config_and_is_idempotent(self):
        links = [self.bin_link(), self.bin_link(nested=True)]
        regular = links[0][0].parent / "regular"
        regular.write_text("keep")
        config = self.cache / ".npmrc"
        config.write_text("fund=false\n")
        result = self.run_function()
        self.assertEqual(result.returncode, 0, result.stderr)
        for link, target in links:
            self.assertFalse(link.is_symlink())
            self.assertEqual(target.read_text(), "library content")
        self.assertEqual(regular.read_text(), "keep")
        self.assertIn("fund=false", config.read_text())
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.cache.rglob("*") if p.is_file()}
        result = self.run_function()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in self.cache.rglob("*") if p.is_file()})

    def test_unexpected_entries_stop_before_any_changes(self):
        for kind in ("outside", "broken", "directory", "other_link", "fifo"):
            with self.subTest(kind=kind):
                good, _ = self.bin_link()
                bad = self.cache / "node_modules/.bin/bad"
                if kind == "fifo":
                    os.mkfifo(bad)
                else:
                    target = self.base / "outside"
                    target.write_text("outside")
                    if kind == "broken":
                        target = self.base / "missing"
                    elif kind == "directory":
                        target = self.cache / "node_modules"
                    elif kind == "other_link":
                        bad = self.cache / "other"
                        target = good.resolve()
                    bad.symlink_to(target)
                result = self.run_function()
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(good.is_symlink())
                self.assertFalse((self.cache / ".npmrc").exists())
                bad.unlink()
                good.unlink()

    def test_cache_discovery_failure(self):
        for payload in ({"installed": []}, {"installed": [{"pluginId": "context-mode@context-mode", "version": "../outside"}]}):
            self.stub("codex", f"print({json.dumps(payload)!r})")
            result = self.run_function()
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.cache / ".npmrc").exists())

    def test_npm_and_trash_failures_propagate(self):
        good, _ = self.bin_link()
        self.stub("npm", "raise SystemExit(1)")
        self.assertNotEqual(self.run_function().returncode, 0)
        self.assertTrue(good.is_symlink())
        self.stub("npm", "print('false')")
        self.stub("trash", "raise SystemExit(1)")
        self.assertNotEqual(self.run_function().returncode, 0)
        self.assertTrue(good.is_symlink())

    def test_ineffective_config_or_removal_is_rejected(self):
        good, _ = self.bin_link()
        self.stub("npm", "print('true')")
        self.assertNotEqual(self.run_function().returncode, 0)
        self.assertTrue(good.is_symlink())
        self.stub("npm", "print('false')")
        self.stub("trash", "pass")
        self.assertNotEqual(self.run_function().returncode, 0)
        self.assertTrue(good.is_symlink())

    def test_setup_repairs_after_fresh_or_existing_install_and_propagates_failure(self):
        for installed in (True, False):
            for repair_exit in (0, 1):
                with self.subTest(installed=installed, repair_exit=repair_exit):
                    self.record.write_text("")
                    payload = '{"installed":[{"pluginId":"context-mode@context-mode"}]}' if installed else '{"installed":[]}'
                    prelude = f'''
setup_context_mode_cli() {{ return 0; }}
require_ai_setup_command() {{ return 0; }}
codex() {{
  if [[ "$2 $3" == "marketplace list" ]]; then
    echo context-mode
  elif [[ "$2 $3" == "list --json" ]]; then
    echo {shlex.quote(payload)}
  elif [[ "$2" == "add" ]]; then
    echo install >> {shlex.quote(str(self.record))}
  fi
}}
repair_codex_context_mode_cache() {{
  echo repair >> {shlex.quote(str(self.record))}
  return {repair_exit}
}}
'''
                    result = self.run_function("setup_codex_context_mode", prelude)
                    self.assertEqual(result.returncode, repair_exit, result.stderr)
                    self.assertEqual(self.record.read_text().splitlines(),
                                     ["repair"] if installed else ["install", "repair"])


if __name__ == "__main__":
    unittest.main()
