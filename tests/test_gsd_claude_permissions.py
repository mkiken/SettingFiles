import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GSD_HELPER = REPO_ROOT / "mac/scripts/ai/gsd_core.sh"
UTILS_HELPER = REPO_ROOT / "shell/zsh/alias/utils.zsh"


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class FixClaudeGsdWritePermissionsTest(unittest.TestCase):
    def run_fix(
        self,
        settings_obj: object | None,
        *,
        confirm_rc: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], object | None, list[str]]:
        """_fix_claude_gsd_write_permissions を使い捨てのsettings.jsonに対して実行する。

        settings_obj=None は「設定ファイルが存在しない」ケースを表す。confirm_rc は
        confirm() のスタブの戻り値(0=承認, 1=拒否)で、確認ステップを非対話で制御する。
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            if settings_obj is not None:
                settings_path.write_text(json.dumps(settings_obj), encoding="utf-8")

            confirm_log = Path(temp_dir) / "confirm.log"

            # utils.zsh を先に source して json_files_semantically_equal の実体を使う。
            # confirm/show_json_diff は非対話テストのため後からスタブで上書きする。
            script = f'''
source "{UTILS_HELPER}"
source "{GSD_HELPER}"

function require_ai_setup_command() {{
  return 0
}}

function confirm() {{
  printf 'called\\n' >> "$CONFIRM_LOG"
  return "$CONFIRM_RC"
}}

function show_json_diff() {{
  return 0
}}

_fix_claude_gsd_write_permissions "$1"
'''
            result = subprocess.run(
                ["zsh", "-c", script, "gsd-perm-test", str(settings_path)],
                cwd=REPO_ROOT,
                env={
                    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
                    "CONFIRM_LOG": str(confirm_log),
                    "CONFIRM_RC": str(confirm_rc),
                },
                capture_output=True,
                text=True,
                check=False,
            )

            data = None
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))

            confirm_calls = (
                confirm_log.read_text(encoding="utf-8").splitlines()
                if confirm_log.exists()
                else []
            )

            return result, data, confirm_calls

    def test_write_only_entries_are_converted_to_edit_when_approved(self):
        before = {
            "permissions": {
                "allow": [
                    "Bash(npx gsd-core *)",
                    "Read(.planning/*)",
                    "Write(.planning/*)",
                    "Read(STATE.md)",
                    "Write(STATE.md)",
                ],
                "deny": [],
            }
        }

        result, after, confirm_calls = self.run_fix(before, confirm_rc=0)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(confirm_calls), 1)
        self.assertEqual(
            after["permissions"]["allow"],
            [
                "Bash(npx gsd-core *)",
                "Read(.planning/*)",
                "Edit(.planning/*)",
                "Read(STATE.md)",
                "Edit(STATE.md)",
            ],
        )

    def test_existing_edit_entry_is_not_duplicated_when_approved(self):
        before = {
            "permissions": {
                "allow": [
                    "Read(.planning/*)",
                    "Write(.planning/*)",
                    "Read(STATE.md)",
                    "Write(STATE.md)",
                    "Edit(.planning/*)",
                ],
            }
        }

        result, after, confirm_calls = self.run_fix(before, confirm_rc=0)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(confirm_calls), 1)
        allow = after["permissions"]["allow"]
        self.assertEqual(allow.count("Edit(.planning/*)"), 1)
        self.assertNotIn("Write(.planning/*)", allow)
        self.assertNotIn("Write(STATE.md)", allow)
        # 変換されたエントリは元のWriteの位置(index 1)を保持する
        self.assertEqual(allow.index("Edit(.planning/*)"), 1)

    def test_declined_confirmation_leaves_settings_unchanged(self):
        before = {
            "permissions": {
                "allow": [
                    "Read(.planning/*)",
                    "Write(.planning/*)",
                    "Read(STATE.md)",
                    "Write(STATE.md)",
                ],
            }
        }

        result, after, confirm_calls = self.run_fix(before, confirm_rc=1)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(confirm_calls), 1)
        self.assertEqual(after, before)

    def test_already_fixed_settings_skip_confirmation(self):
        before = {
            "permissions": {
                "allow": [
                    "Bash(npx gsd-core *)",
                    "Read(.planning/*)",
                    "Edit(.planning/*)",
                    "Read(STATE.md)",
                    "Edit(STATE.md)",
                ],
            }
        }

        result, after, confirm_calls = self.run_fix(before, confirm_rc=0)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(confirm_calls, [])
        self.assertEqual(after, before)

    def test_missing_permissions_allow_is_left_untouched(self):
        cases = {
            "no permissions key": {"model": "sonnet"},
            "permissions without allow": {"permissions": {"deny": ["Read(.env)"]}},
        }

        for name, before in cases.items():
            with self.subTest(case=name):
                result, after, confirm_calls = self.run_fix(before, confirm_rc=0)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(confirm_calls, [])
                self.assertEqual(after, before)

    def test_missing_settings_file_is_a_noop(self):
        result, after, confirm_calls = self.run_fix(None, confirm_rc=0)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(confirm_calls, [])
        self.assertIsNone(after)

    def test_key_order_and_machine_local_keys_survive_approval(self):
        before = {
            "model": "sonnet",
            "permissions": {
                "allow": [
                    "Read(.planning/*)",
                    "Write(.planning/*)",
                ],
                "deny": ["Read(.env)"],
            },
            "statusLine": {"type": "command", "command": "echo hi"},
            "machineLocalKey": "keepme",
        }

        result, after, confirm_calls = self.run_fix(before, confirm_rc=0)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(confirm_calls), 1)
        self.assertEqual(list(after.keys()), list(before.keys()))
        self.assertEqual(after["statusLine"], before["statusLine"])
        self.assertEqual(after["machineLocalKey"], "keepme")
        self.assertEqual(after["permissions"]["deny"], ["Read(.env)"])
        self.assertEqual(after["permissions"]["allow"], ["Read(.planning/*)", "Edit(.planning/*)"])

    def test_claude_branch_invokes_permission_fix_with_confirmation(self):
        helper = read_text("mac/scripts/ai/gsd_core.sh")

        self.assertIn('elif [[ "$runtime" == "claude" ]]', helper)
        self.assertIn("_fix_claude_gsd_write_permissions || return 1", helper)
        self.assertIn("require_ai_setup_command jq || return 1", helper)
        self.assertIn("show_json_diff", helper)
        self.assertIn("confirm ", helper)
        self.assertIn("json_files_semantically_equal", helper)


if __name__ == "__main__":
    unittest.main()
