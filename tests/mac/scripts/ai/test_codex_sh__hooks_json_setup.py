import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

SCRIPT = REPO_ROOT / "mac/scripts/ai/codex.sh"
UTILS = REPO_ROOT / "shell/zsh/alias/utils.zsh"

REPO_HOOKS = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "repo-stop"}]}]}}
LIVE_HOOKS = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "orca-stop"}]}]}}


class CodexHooksJsonSetupTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        (self.repo / "ai/codex").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)
        self.source = self.repo / "ai/codex/hooks.json"
        self.source.write_text(json.dumps(REPO_HOOKS), encoding="utf-8")
        self.live = self.home / ".codex/hooks.json"

    def setup_hooks(self):
        # merge_src を指定して対話プロンプトを避ける
        return subprocess.run(
            ["zsh", "-c",
             'Repo="$4/"; source "$3"; source "$5"; Repo="$1/"; HOME="$2"; setup_codex_hooks_json',
             "test", str(self.repo), str(self.home), str(SCRIPT), str(REPO_ROOT), str(UTILS)],
            env=sanitized_env({"SMART_MERGE_ACTION": "merge_src",
                               "XDG_STATE_HOME": str(self.root / "state")}),
            text=True, capture_output=True,
        )

    def commands(self, path):
        stop = json.loads(path.read_text(encoding="utf-8"))["hooks"]["Stop"]
        return {h["command"] for entry in stop for h in entry["hooks"]}

    def test_missing_live_file_is_created_as_regular_file(self):
        result = self.setup_hooks()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.live.is_symlink())
        self.assertEqual(self.commands(self.live), {"repo-stop"})

    def test_legacy_symlink_becomes_regular_file_and_repo_stays_untouched(self):
        # 旧方式: live がリポジトリ側 hooks.json への symlink。merge が symlink 経由で
        # リポジトリへ書き込まないことを、リポジトリ内容を変える差分を持つ状態で確認する。
        self.live.symlink_to(self.source)
        repo_before = self.source.read_bytes()

        result = self.setup_hooks()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.live.is_symlink())
        self.assertEqual(self.source.read_bytes(), repo_before)

    def test_live_only_entries_are_preserved_on_merge(self):
        self.live.write_text(json.dumps(LIVE_HOOKS), encoding="utf-8")

        result = self.setup_hooks()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(self.live), {"repo-stop", "orca-stop"})

    def test_setup_scripts_call_helper_instead_of_symlinking_hooks_json(self):
        for rel in ("mac/initialization/ai/codex.sh", "mac/updates/codex.sh"):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("setup_codex_hooks_json", text, rel)
            # symlink だと外部ツールの追記がリポジトリへ書き込まれるため禁止
            self.assertNotIn('ai/codex/hooks.json" ~/.codex/hooks.json', text, rel)


if __name__ == "__main__":
    unittest.main()
