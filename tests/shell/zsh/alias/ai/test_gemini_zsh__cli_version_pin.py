import json
import shlex
import subprocess
import unittest

from support import REPO_ROOT, sanitized_env

GEMINI_ZSH = REPO_ROOT / "shell/zsh/alias/ai/gemini.zsh"
PINNED_VERSION = "0.60.0"
INSTALL_SCRIPTS = [
    REPO_ROOT / "mac/initialization/ai/gemini.sh",
    REPO_ROOT / "mac/updates/gemini.sh",
]


class GeminiCliVersionPinTest(unittest.TestCase):
    def test_gm_update_installs_pinned_version(self):
        script = f'''
homebrew_npm() {{
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@"
}}
source {shlex.quote(str(GEMINI_ZSH))}
gm-update
'''
        result = subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env=sanitized_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["install", "-g", f"@google/gemini-cli@{PINNED_VERSION}"],
        )

    def test_install_scripts_delegate_to_gm_update(self):
        for path in INSTALL_SCRIPTS:
            with self.subTest(script=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("gm-update", text)
                # 固定が外れる @latest の直書きを各スクリプトに再導入させない
                # （0.61.0 以降の Untrusted Command Flags 誤検知を避けるため gm-update で一元管理）。
                self.assertNotIn("gemini-cli@", text)

    def test_repo_settings_disable_gemini_auto_update(self):
        settings = json.loads(
            (REPO_ROOT / "ai/gemini/settings.json").read_text(encoding="utf-8")
        )
        # Gemini の自動更新で固定が外れた実例（0.63.0 への勝手な更新）があるため baseline で無効化する。
        self.assertIs(settings["general"]["enableAutoUpdate"], False)


if __name__ == "__main__":
    unittest.main()
