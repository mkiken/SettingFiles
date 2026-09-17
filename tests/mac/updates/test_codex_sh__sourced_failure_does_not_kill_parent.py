import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT, sanitized_env

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class CodexUpdateSourcedFailureTest(unittest.TestCase):
    """mac/updates/codex.sh が source され、内部の update_codex_caveman が失敗しても、
    呼び出し元 (mac/update 相当) のスクリプトが死なずに後続へ進むことを確認する。

    update_codex_caveman は mac/updates/codex.sh 内で
    "${Repo}mac/scripts/ai/codex.sh" を source した後に呼ばれるため、
    外側で関数をスタブしても上書きされてしまう。そこで
    update_codex_caveman の呼び出し行だけを、確実に失敗するスタブ関数呼び出しに
    差し替えたコピーを使い捨てディレクトリに置いて検証する
    （実際の npm/npx 更新や caveman skill 取得には一切触れない）。
    """

    def test_parent_script_continues_after_codex_caveman_update_fails(self):
        codex_update_source = (REPO_ROOT / "mac/updates/codex.sh").read_text(encoding="utf-8")
        broken_source = codex_update_source.replace(
            "update_codex_caveman || return 1",
            "_test_failing_stub || return 1",
        )
        self.assertNotEqual(
            codex_update_source, broken_source, "update_codex_caveman 呼び出し行の置換に失敗した"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            updates_dir = Path(tmp_dir) / "mac" / "updates"
            updates_dir.mkdir(parents=True)
            broken_codex_update = updates_dir / "codex.sh"
            broken_codex_update.write_text(broken_source, encoding="utf-8")

            wrapper_path = Path(tmp_dir) / "parent_wrapper.sh"
            wrapper_path.write_text(
                f'source "{REPO_ROOT}/mac/scripts/common.sh"\n'
                # npm i -g / npx --yes cc-sdd@latest は codex.sh 冒頭で無条件実行される。
                # 本テストは update_codex_caveman の失敗継続だけを検証したいので、
                # 実際のネットワークインストールに触れないようどちらも no-op に潰す。
                "function npm() { return 0; }\n"
                "function npx() { return 0; }\n"
                "function _test_failing_stub() { return 1; }\n"
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
            # 親スクリプトが exit で即死していれば以下は絶対に出力されない
            self.assertIn("after codex step: status=1", output)


if __name__ == "__main__":
    unittest.main()
