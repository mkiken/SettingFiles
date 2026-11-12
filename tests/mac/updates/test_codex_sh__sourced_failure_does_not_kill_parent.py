import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT, sanitized_env

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class CodexUpdateSourcedFailureTest(unittest.TestCase):
    def test_parent_script_continues_after_hooks_setup_fails(self):
        codex_update_source = (REPO_ROOT / "mac/updates/codex.sh").read_text(encoding="utf-8")
        # Keep the real failure guard while replacing sourced setup with isolated stubs.
        broken_source = codex_update_source.replace(
            'source "$(dirname "$0")/../scripts/common.sh"', ":"
        ).replace('source "${Repo}mac/scripts/ai/codex.sh"', ":")
        self.assertNotEqual(codex_update_source, broken_source)
        self.assertIn("setup_codex_hooks_json || return 1", broken_source)

        with tempfile.TemporaryDirectory() as tmp_dir:
            updates_dir = Path(tmp_dir) / "mac" / "updates"
            updates_dir.mkdir(parents=True)
            broken_codex_update = updates_dir / "codex.sh"
            broken_codex_update.write_text(broken_source, encoding="utf-8")

            wrapper_path = Path(tmp_dir) / "parent_wrapper.sh"
            wrapper_path.write_text(
                f'Repo="{REPO_ROOT}/"\n'
                "function npm() { return 0; }\n"
                "function npx() { return 0; }\n"
                "function setup_ai_mcp() { return 0; }\n"
                "function setup_ai_pr_tools() { return 0; }\n"
                "function generate_codex_agents() { return 0; }\n"
                "function make_symlink() { return 0; }\n"
                "function setup_codex_hooks_json() { echo hooks-failed; return 1; }\n"
                'echo "before codex step"\n'
                f'source "{broken_codex_update}"\n'
                'echo "after codex step: status=$?"\n',
                encoding="utf-8",
            )

            result = subprocess.run(
                ["zsh", str(wrapper_path)],
                cwd=REPO_ROOT,
                env=sanitized_env({"HOME": tmp_dir, "PATH": SYSTEM_PATH, "LANG": "en_US.UTF-8"}),
                text=True,
                capture_output=True,
                check=False,
            )
            output = result.stdout + result.stderr

            self.assertIn("before codex step", output)
            self.assertIn("hooks-failed", output)
            # 親スクリプトが exit で即死していれば以下は絶対に出力されない
            self.assertIn("after codex step: status=1", output)


if __name__ == "__main__":
    unittest.main()
