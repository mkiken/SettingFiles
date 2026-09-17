import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT, sanitized_env

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class HerdrUpdateSourcedFailureTest(unittest.TestCase):
    """mac/updates/herdr.sh が source され、内部の setup_herdr が失敗しても、
    呼び出し元 (mac/update 相当) のスクリプトが死なずに後続へ進むことを確認する。

    setup_herdr は mac/updates/herdr.sh 内で "${Repo}mac/scripts/herdr.sh" を
    source した後に呼ばれるため、外側から関数をスタブしても上書きされてしまう。
    そこで setup_herdr 自身が確実に失敗する経路 —
    setup_herdr_integrations が検証する不正な mode 文字列を第3引数に渡す —
    を使い、実際の Herdr integration やライブ設定には一切触れずに検証する。
    このラッパー自身は mac/updates/herdr.sh を書き換えたコピーとして
    使い捨てディレクトリに置き、mode を固定引数から差し替え可能にする。
    """

    def test_parent_script_continues_after_herdr_update_fails(self):
        herdr_update_source = (REPO_ROOT / "mac/updates/herdr.sh").read_text(encoding="utf-8")
        # setup_herdr の mode 引数を不正値に差し替え、確実に失敗させる。
        broken_source = herdr_update_source.replace(
            'setup_herdr "" "" update || return 1',
            'setup_herdr "" "" bogus-mode || return 1',
        )
        self.assertNotEqual(
            herdr_update_source, broken_source, "setup_herdr 呼び出し行の置換に失敗した"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            updates_dir = Path(tmp_dir) / "mac" / "updates"
            updates_dir.mkdir(parents=True)
            broken_herdr_update = updates_dir / "herdr.sh"
            broken_herdr_update.write_text(broken_source, encoding="utf-8")

            wrapper_path = Path(tmp_dir) / "parent_wrapper.sh"
            wrapper_path.write_text(
                f'source "{REPO_ROOT}/mac/scripts/common.sh"\n'
                'echo "before herdr step"\n'
                f'source "{broken_herdr_update}"\n'
                'echo "after herdr step: status=$?"\n',
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

            self.assertIn("before herdr step", output)
            # 親スクリプトが exit で即死していれば以下は絶対に出力されない
            self.assertIn("after herdr step: status=1", output)


if __name__ == "__main__":
    unittest.main()
