# AIレビュー統合フロー Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3AI並列PRレビューの結果をファイル集約し、完了監視→意味マージ→HTMLレポート→採用項目のPR投稿/修正までを一本のフローにする。

**Architecture:** 各AIレビュースキルが環境変数 `AI_REVIEW_OUTPUT_FILE` 指定時に最終出力をランディレクトリへ複製書き出し。シェルランチャーがランディレクトリを作成して3AIを新規タブ起動し、元タブのウォッチャーが揃いをポーリングして `review-merge` スキル(Claude)を自動起動。マージAIは意味的重複統合のみ行い、決定的Pythonスクリプトが `merged.json` → `report.html` を生成。ブラウザ(Chrome系、File System Access API)がチェック状態を `state.json` に自動保存し、`review-post` / `review-fix` スキル(Claude/Codex)がそれを読んで投稿/修正する。

**Tech Stack:** zsh/bash (ランチャー・ウォッチャー), Python 3 標準ライブラリ (レンダリング), 素のHTML/CSS/JS (レポート), 共有コアスキル機構 (ai/common + アダプタ + generate_codex_skills)。

**Spec:** `docs/superpowers/specs/2026-07-26-ai-review-merge-flow-design.md`

## Global Constraints

- コミット対象ソースに個人絶対パスを書かない(`$HOME`/`~` を使う。ai/CLAUDE.md「No Personal Paths」)。
- 削除は必ず `trash`(引数にrm系フラグ不可)。`rm`/`/bin/rm` は permission-denied。
- AIプロンプトファイルの新規内容は英語・簡潔に(CLAUDE.md「AI Prompt File Editing」)。
- 生成物(Codex `SKILL.md`)は直接編集せずソース編集→再生成→`verify_ai_skill_generation_idempotency`。
- テストは `python3 -m unittest discover -s tests` に統合。シェル関数はPythonから `bash -c`(zsh関数は `zsh -c`)で呼ぶ既存流儀(`tests/shell/tmux/test_ai_notification_summary_sh.py` の `run_fn` 参照)。
- コミットは czg 形式 `<type>(<scope>): <emoji> <subject>`(subject 50字以内・小文字始まり)。scope は `.commitlintrc.json` の enum から。
- zsh: 一時変数名に `path`/`status` を使わない。`$(...)` 内の cd は `builtin cd -q`。
- 破壊的コマンドを含むコードの検証は必ず使い捨てディレクトリ(`mktemp -d`)で行う。テストから `trash` を呼ぶ経路は必ずスタブに差し替える。
- 環境変数名は `AI_REVIEW_OUTPUT_FILE` / `AI_REVIEW_CACHE_ROOT` / `AI_REVIEW_RUN_ID` / `AI_REVIEW_KEEP_RUNS` / `AI_REVIEW_WAIT_INTERVAL` / `AI_REVIEW_WAIT_TIMEOUT` で統一。
- 各タスク末尾のコミットは、コミット前に `git diff --cached --name-only` で自セッションのパスだけが載っていることを確認してから行う(CLAUDE.md 並行セッション規約)。

## File Structure

新規:

- `shell/common/pr/ai_review_run_dir.sh` — ランディレクトリ作成/latest解決/保持ポリシー(bash、source可能+CLI)
- `shell/common/pr/ai_review_wait.sh` — 結果ファイル揃い待ちウォッチャー(bash CLI)
- `shell/common/pr/generate_review_report.py` — merged.json → report.html(テンプレート内蔵)
- `ai/common/review_merge_core.md` / `ai/common/review_post_core.md` / `ai/common/review_fix_core.md` — 新スキル共有コア
- `ai/common/pr_post_mechanics_core.md` — pr-comment-postから分離する投稿メカニクス
- `ai/claude/skills/{review-merge,review-post,review-fix}/SKILL.md` — Claudeアダプタ
- `ai/codex/skills/{review-merge,review-post,review-fix}/skill_head.md`(+生成される `SKILL.md`)
- `tests/shell/common/pr/test_ai_review_run_dir_sh.py` / `tests/shell/common/pr/test_ai_review_wait_sh.py` / `tests/shell/common/pr/test_generate_review_report.py` / `tests/shell/zsh/alias/ai/test_ai_zsh__ai_review_launcher.py`

変更:

- `ai/common/pr_review_core.md`, `ai/common/pr_review_subagents/orchestrator_core.md` — 書き出し指示追加
- `ai/common/pr_comment_post_core.md` — メカニクス分離
- `ai/claude/skills/pr-comment-post/SKILL.md`, `ai/gemini/commands/pr-comment-post.toml` — コア2分割への追従
- `ai/codex/skills/*/SKILL.md` — 再生成
- `mac/scripts/common.sh` — `generate_codex_skills` エントリ追加、`setup_ai_pr_tools` の *.py 対応
- `shell/common/alias/claude.sh` — `cl-review-merge` / `cl-review-post` / `cl-review-fix`
- `shell/zsh/alias/ai/codex.zsh` — `cx-review-merge` / `cx-review-post` / `cx-review-fix`
- `shell/zsh/alias/ai/gemini.zsh` — `gm-pr-review` を yolo 化
- `shell/zsh/alias/ai/ai.zsh` — 自動チェーン組込み、review-all削除
- `CLAUDE.md` — スキル構成表の更新

---

### Task 1: ランディレクトリ管理スクリプト

**Files:**
- Create: `shell/common/pr/ai_review_run_dir.sh`
- Test: `tests/shell/common/pr/test_ai_review_run_dir_sh.py`

**Interfaces:**
- Produces: CLI `ai_review_run_dir.sh <pr_number>` → 新規ランディレクトリの絶対パスをstdoutに1行出力(作成・latest更新・保持ポリシー適用込み)。`ai_review_run_dir.sh --latest <pr_number>` → 最新ランディレクトリの実体パスを出力(作成しない、無ければ非0)。環境変数 `AI_REVIEW_CACHE_ROOT`(default `~/.cache/ai-review`)、`AI_REVIEW_RUN_ID`(テスト用run-id固定)、`AI_REVIEW_KEEP_RUNS`(default 5)。カレントディレクトリのgit remote originからslug(`owner__repo`)を解決する。

- [ ] **Step 1: 失敗するテストを書く**

`tests/shell/common/pr/test_ai_review_run_dir_sh.py` を作成。既存 `tests/shell/tmux/test_ai_notification_summary_sh.py` の「シェルをPythonから叩く」流儀に合わせる。テンポラリgitリポジトリ+スタブtrash+`AI_REVIEW_CACHE_ROOT` で完全隔離する。

```python
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_review_run_dir.sh"


class AiReviewRunDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.work = base / "work"
        self.cache = base / "cache"
        self.bin = base / "bin"
        self.trash_log = base / "trash.log"
        self.work.mkdir()
        self.bin.mkdir()
        # trashスタブ: 呼び出しをログに追記し、実体をmvで退避する(rm系は使わない)
        trash_stub = self.bin / "trash"
        trash_stub.write_text(
            "#!/bin/bash\n"
            f'printf \'%s\\n\' "$@" >> "{self.trash_log}"\n'
            f'mkdir -p "{base}/trashed"\n'
            f'mv "$@" "{base}/trashed/"\n'
        )
        trash_stub.chmod(trash_stub.stat().st_mode | stat.S_IEXEC)
        subprocess.run(["git", "init", "-q"], cwd=self.work, check=True)

    def run_script(self, *args, remote="git@github.com:owner/repo.git", run_id="20260726-0000"):
        subprocess.run(
            ["git", "remote", "remove", "origin"],
            cwd=self.work, capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", remote],
            cwd=self.work, check=True,
        )
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            AI_REVIEW_CACHE_ROOT=str(self.cache),
            AI_REVIEW_RUN_ID=run_id,
        )
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=self.work, env=env, capture_output=True, text=True,
        )

    def test_create_outputs_run_dir_and_latest_link(self):
        result = self.run_script("123")
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = Path(result.stdout.strip())
        self.assertTrue(run_dir.is_dir())
        self.assertEqual(run_dir.name, "20260726-0000")
        self.assertEqual(run_dir.parent.name, "pr-123")
        self.assertEqual(run_dir.parent.parent.name, "owner__repo")
        latest = run_dir.parent / "latest"
        self.assertTrue(latest.is_symlink())
        self.assertEqual(os.readlink(latest), "20260726-0000")

    def test_repo_slug_parsing(self):
        cases = [
            ("git@github.com:owner/repo.git", "owner__repo"),
            ("https://github.com/owner/repo.git", "owner__repo"),
            ("https://github.com/owner/repo", "owner__repo"),
            ("ssh://git@github.com/owner/repo.git", "owner__repo"),
        ]
        for remote, expected in cases:
            with self.subTest(remote=remote):
                result = self.run_script("7", remote=remote)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"/{expected}/pr-7/", result.stdout)

    def test_latest_resolves_newest_run(self):
        self.run_script("123", run_id="20260726-0000")
        self.run_script("123", run_id="20260726-0100")
        result = self.run_script("--latest", "123")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith("pr-123/20260726-0100"))

    def test_latest_fails_when_no_runs(self):
        result = self.run_script("--latest", "999")
        self.assertNotEqual(result.returncode, 0)

    def test_retention_trashes_only_beyond_keep(self):
        # 境界値: keep=5 に対して 4, 5, 7 ラン
        cases = [(4, 0), (5, 0), (7, 2)]
        for total, expected_trashed in cases:
            with self.subTest(total=total):
                if self.trash_log.exists():
                    self.trash_log.unlink()
                for i in range(total):
                    self.run_script(str(1000 + total), run_id=f"20260726-{i:04d}")
                trashed = (
                    self.trash_log.read_text().strip().splitlines()
                    if self.trash_log.exists() else []
                )
                self.assertEqual(len(trashed), expected_trashed)
                if expected_trashed:
                    # 最古のランから順にtrashされる
                    self.assertTrue(trashed[0].endswith("20260726-0000"))

    def test_missing_pr_number_fails(self):
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m unittest tests.test_ai_review_run_dir -v`
Expected: 全ケースFAIL(スクリプト不在)。

- [ ] **Step 3: スクリプトを実装**

`shell/common/pr/ai_review_run_dir.sh`:

```bash
#!/bin/bash
# AIレビューのランディレクトリ管理。
# 使い方:
#   ai_review_run_dir.sh <pr_number>            新規ランディレクトリを作成しパスを出力
#   ai_review_run_dir.sh --latest <pr_number>   最新ランディレクトリの実体パスを出力(作成しない)
# 環境変数:
#   AI_REVIEW_CACHE_ROOT  ベースディレクトリ(default: ~/.cache/ai-review)
#   AI_REVIEW_RUN_ID      run-idの固定(テスト用。default: date +%Y%m%d-%H%M%S)
#   AI_REVIEW_KEEP_RUNS   PRごとの保持ラン数(default: 5)

set -u

ai_review_repo_slug() {
    local url
    url=$(git remote get-url origin 2>/dev/null) || {
        echo "git remote origin が見つかりません" >&2
        return 1
    }
    local trimmed="${url%.git}"
    trimmed="${trimmed#ssh://}"
    trimmed="${trimmed#git@}"
    trimmed="${trimmed#https://}"
    trimmed="${trimmed#http://}"
    # scp形式 host:owner/repo をパス形式に揃える
    trimmed="${trimmed/:/\/}"
    local repo="${trimmed##*/}"
    local rest="${trimmed%/*}"
    local owner="${rest##*/}"
    if [[ -z "$owner" || -z "$repo" || "$owner" == "$trimmed" ]]; then
        echo "originのURLからowner/repoを解決できません: $url" >&2
        return 1
    fi
    printf '%s__%s\n' "$owner" "$repo"
}

ai_review_pr_dir() {
    local pr_number="$1"
    local slug
    slug=$(ai_review_repo_slug) || return 1
    printf '%s/%s/pr-%s\n' \
        "${AI_REVIEW_CACHE_ROOT:-$HOME/.cache/ai-review}" "$slug" "$pr_number"
}

ai_review_latest_run_dir() {
    local pr_dir
    pr_dir=$(ai_review_pr_dir "$1") || return 1
    local latest="${pr_dir}/latest"
    if [[ ! -d "$latest" ]]; then
        echo "最新ランが見つかりません: $latest" >&2
        return 1
    fi
    (cd "$latest" && pwd -P)
}

ai_review_prune_old_runs() {
    local pr_dir="$1"
    local keep="${AI_REVIEW_KEEP_RUNS:-5}"
    local -a runs=()
    local line
    # run-id形式(数字-数字)のディレクトリのみ対象。latestリンクは-type dに一致しない
    while IFS= read -r line; do
        runs+=("$line")
    done < <(find "$pr_dir" -mindepth 1 -maxdepth 1 -type d -name '[0-9]*-[0-9]*' | sort)
    local excess=$(( ${#runs[@]} - keep ))
    local i
    for (( i = 0; i < excess; i++ )); do
        trash "${runs[i]}"
    done
}

ai_review_create_run_dir() {
    local pr_number="$1"
    local pr_dir run_id run_dir
    pr_dir=$(ai_review_pr_dir "$pr_number") || return 1
    run_id="${AI_REVIEW_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
    run_dir="${pr_dir}/${run_id}"
    mkdir -p "$run_dir"
    ln -sfn "$run_id" "${pr_dir}/latest"
    ai_review_prune_old_runs "$pr_dir"
    printf '%s\n' "$run_dir"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [[ "${1:-}" == "--latest" ]]; then
        shift
        ai_review_latest_run_dir "${1:?PR番号が必要です}"
    else
        ai_review_create_run_dir "${1:?PR番号が必要です}"
    fi
fi
```

注意: macOSのbashは3.2。`local -a runs=()` と `${#runs[@]}` は3.2でも安全だが、空配列の `"${runs[@]}"` 展開は `set -u` で死ぬため使っていない。同一run-idで再実行した場合は同じディレクトリを再利用する(mkdir -pで冪等)。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m unittest tests.test_ai_review_run_dir -v`
Expected: 全PASS。

- [ ] **Step 5: コミット**

```bash
git add shell/common/pr/ai_review_run_dir.sh tests/shell/common/pr/test_ai_review_run_dir_sh.py
git commit -m "feat(shell): ✨ AIレビューのランディレクトリ管理を追加"
```

---

### Task 2: 完了監視ウォッチャー

**Files:**
- Create: `shell/common/pr/ai_review_wait.sh`
- Test: `tests/shell/common/pr/test_ai_review_wait_sh.py`

**Interfaces:**
- Produces: CLI `ai_review_wait.sh <run_dir> <file...>` — 指定ファイルが全て非空で存在するまでポーリング。進捗はstderrに1行上書き表示。終了コード: 0=揃った / 1=引数不正 / 2=タイムアウト。環境変数 `AI_REVIEW_WAIT_INTERVAL`(default 5秒)、`AI_REVIEW_WAIT_TIMEOUT`(default 7200秒)。

- [ ] **Step 1: 失敗するテストを書く**

`tests/shell/common/pr/test_ai_review_wait_sh.py`:

```python
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_review_wait.sh"


class AiReviewWaitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = Path(self.tmp.name)

    def run_wait(self, *files, interval="0.05", timeout="1"):
        env = dict(
            os.environ,
            AI_REVIEW_WAIT_INTERVAL=interval,
            AI_REVIEW_WAIT_TIMEOUT=timeout,
        )
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir), *files],
            env=env, capture_output=True, text=True,
        )

    def test_returns_zero_when_all_present(self):
        (self.run_dir / "claude.md").write_text("result")
        (self.run_dir / "codex.md").write_text("result")
        result = self.run_wait("claude.md", "codex.md")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_file_does_not_count_as_done(self):
        (self.run_dir / "claude.md").write_text("")
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)

    def test_times_out_when_file_missing(self):
        result = self.run_wait("claude.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("タイムアウト", result.stderr)

    def test_detects_file_created_during_wait(self):
        def create_later():
            time.sleep(0.3)
            (self.run_dir / "claude.md").write_text("result")

        thread = threading.Thread(target=create_later)
        thread.start()
        result = self.run_wait("claude.md", timeout="5")
        thread.join()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_usage_error_without_files(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m unittest tests.test_ai_review_wait -v`
Expected: 全FAIL(スクリプト不在)。

- [ ] **Step 3: スクリプトを実装**

`shell/common/pr/ai_review_wait.sh`:

```bash
#!/bin/bash
# ランディレクトリに期待する結果ファイルが全て(非空で)揃うまでポーリングして待つ。
# 使い方: ai_review_wait.sh <run_dir> <file...>
# 環境変数: AI_REVIEW_WAIT_INTERVAL(default 5) / AI_REVIEW_WAIT_TIMEOUT(default 7200)
# 終了コード: 0=揃った / 1=引数不正 / 2=タイムアウト
# 進捗表示はstderr(1行上書き)。中断はCtrl-C。

set -u

main() {
    local run_dir="${1:-}"
    if [[ -z "$run_dir" || $# -lt 2 ]]; then
        echo "Usage: ai_review_wait.sh <run_dir> <file...>" >&2
        return 1
    fi
    shift

    local interval="${AI_REVIEW_WAIT_INTERVAL:-5}"
    local timeout="${AI_REVIEW_WAIT_TIMEOUT:-7200}"
    local start_epoch elapsed
    start_epoch=$(date +%s)

    while :; do
        local pending=0 status_line="" f
        for f in "$@"; do
            if [[ -s "${run_dir}/${f}" ]]; then
                status_line+=" ${f%.md} ✓"
            else
                status_line+=" ${f%.md} …"
                pending=1
            fi
        done
        elapsed=$(( $(date +%s) - start_epoch ))
        printf '\r\033[Kレビュー完了待ち:%s (%ds)' "$status_line" "$elapsed" >&2
        if (( pending == 0 )); then
            printf '\n' >&2
            return 0
        fi
        if (( elapsed >= timeout )); then
            printf '\nタイムアウト(%ds)。揃った分だけでマージするには review-merge を手動実行してください。\n' "$timeout" >&2
            return 2
        fi
        sleep "$interval"
    done
}

main "$@"
```

非空チェック(`-s`)は、書き出し途中の空ファイルを完了と誤認しないための保険。AI側の書き出しは単一のWriteで行われる想定のため、部分書き込みを読むリスクは実用上無視できる。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m unittest tests.test_ai_review_wait -v`
Expected: 全PASS。

- [ ] **Step 5: コミット**

```bash
git add shell/common/pr/ai_review_wait.sh tests/shell/common/pr/test_ai_review_wait_sh.py
git commit -m "feat(shell): ✨ レビュー結果の完了監視ウォッチャーを追加"
```

---

### Task 3: HTMLレポートレンダリングスクリプト

**Files:**
- Create: `shell/common/pr/generate_review_report.py`
- Modify: `mac/scripts/common.sh` の `setup_ai_pr_tools`(*.py も個別symlink対象に)
- Test: `tests/shell/common/pr/test_generate_review_report.py`

**Interfaces:**
- Consumes: `merged.json`(スキーマはTask 6のコアに定義。本タスクはその形を前提にする)
- Produces: CLI `python3 generate_review_report.py <merged.json> <output.html>`、Python関数 `render(merged: dict) -> str`。生成HTMLは自己完結・Chrome系前提・File System Access APIで `state.json`(`{"schema_version":1,"items":{"<id>":{"reviewed":bool,"adopt":bool}}}`)を保存。

- [ ] **Step 1: 失敗するテストを書く**

`tests/shell/common/pr/test_generate_review_report.py`:

```python
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "generate_review_report.py"

spec = importlib.util.spec_from_file_location("generate_review_report", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def merged(items):
    return {
        "schema_version": 1,
        "pr_number": 123,
        "head_ref_oid": "abc123",
        "run_dir": "/tmp/run",
        "sources": ["claude", "codex"],
        "items": items,
    }


def item(id_, **overrides):
    base = {
        "id": id_,
        "file": "src/app.py",
        "line_spec": "42",
        "area": "バグ検出",
        "priority": "high",
        "summary": "サンプル指摘",
        "carryover": None,
        "sources": [
            {"ai": "claude", "original_number": 1, "priority": "high",
             "impact": "High", "confidence": 85, "text": "詳細説明"},
        ],
    }
    base.update(overrides)
    return base


class RenderTest(unittest.TestCase):
    def test_render_embeds_data_and_placeholder_removed(self):
        html = mod.render(merged([item(1)]))
        self.assertIn('"pr_number": 123'.replace(" ", ""),
                      html.replace(" ", ""))
        self.assertNotIn("__REVIEW_DATA__", html)

    def test_render_priorities_table_driven(self):
        cases = ["high", "medium", "low"]
        for prio in cases:
            with self.subTest(prio=prio):
                html = mod.render(merged([item(1, priority=prio)]))
                self.assertIn("サンプル指摘", html)

    def test_render_zero_items(self):
        html = mod.render(merged([]))
        self.assertIn("<html", html)
        self.assertNotIn("__REVIEW_DATA__", html)

    def test_script_close_tag_escaped(self):
        html = mod.render(merged([item(1, summary="悪意ある</script>タグ")]))
        # 埋め込みJSON内で </ が <\/ にエスケープされ、scriptが早期閉鎖されない
        self.assertNotIn("悪意ある</script>", html)
        self.assertIn("悪意ある<\\/script>", html)

    def test_multi_source_and_carryover(self):
        it = item(
            1,
            carryover="skipped_before",
            sources=[
                {"ai": "claude", "original_number": 1, "priority": "high",
                 "impact": "High", "confidence": 85, "text": "claude詳細"},
                {"ai": "codex", "original_number": 3, "priority": "medium",
                 "impact": "Medium", "confidence": 70, "text": "codex詳細"},
            ],
        )
        html = mod.render(merged([it]))
        self.assertIn("claude詳細", html)
        self.assertIn("codex詳細", html)
        self.assertIn("skipped_before", html)


class MainTest(unittest.TestCase):
    def test_main_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "merged.json"
            dst = Path(tmp) / "report.html"
            src.write_text(json.dumps(merged([item(1)])), encoding="utf-8")
            rc = mod.main(["prog", str(src), str(dst)])
            self.assertEqual(rc, 0)
            self.assertIn("サンプル指摘", dst.read_text(encoding="utf-8"))

    def test_main_usage_error(self):
        self.assertEqual(mod.main(["prog"]), 1)


if __name__ == "__main__":
    unittest.main()
```

補足: `test_render_zero_items` は「0件でも例外なくHTMLが生成される」ことの確認が本質。アサーションは `<html` を含むことのシンプルな形に直してよい(`self.assertIn("<html", html)`)。

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m unittest tests.test_generate_review_report -v`
Expected: 全FAIL(スクリプト不在)。

- [ ] **Step 3: スクリプトを実装**

`shell/common/pr/generate_review_report.py`。データはJSONとして埋め込み、DOM構築はJSが `textContent` ベースで行う(HTMLエスケープ漏れを構造的に防ぐ)。JSON埋め込みは `</` → `<\/` エスケープで `</script>` 早期閉鎖を防止。

````python
#!/usr/bin/env python3
"""merged.json から自己完結の report.html を生成する。

使い方: generate_review_report.py <merged.json> <output.html>

- テンプレートは本ファイルに内蔵(単一ファイル配備)。
- データはJSONとしてページに埋め込み、DOM構築はクライアントJSが
  textContent ベースで行う(エスケープ漏れ防止)。
- チェック状態は File System Access API で state.json に保存する
  (Chrome系前提。スキーマ: {"schema_version":1,"items":{"<id>":{"reviewed":bool,"adopt":bool}}})。
"""
import json
import sys

HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Review Report</title>
<style>
:root{--bg:#f6f8fa;--card:#fff;--border:#d1d9e0;--text:#1f2328;--muted:#59636e;
--high:#d1242f;--medium:#bf8700;--low:#1a7f37;
--claude:#d97757;--gemini:#4285f4;--codex:#10a37f;}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#151b23;
--border:#3d444d;--text:#f0f6fc;--muted:#9198a1;}}
*{box-sizing:border-box}
body{margin:0;padding:16px 16px 90px;background:var(--bg);color:var(--text);
font-family:-apple-system,"Hiragino Sans",sans-serif;font-size:14px;line-height:1.6}
h1{font-size:18px;margin:0 0 4px}
.meta{color:var(--muted);margin-bottom:12px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
button{cursor:pointer;border:1px solid var(--border);background:var(--card);
color:var(--text);border-radius:6px;padding:4px 12px;font-size:13px}
.prio-title{margin:20px 0 8px;font-size:15px}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px}
.card.adopted{border-left:4px solid var(--low)}
.card-header{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;flex-wrap:wrap}
.card-header .summary{flex:1;min-width:200px;font-weight:600}
.card.reviewed .summary{opacity:.55}
.badge{display:inline-block;border-radius:10px;padding:0 8px;font-size:11px;
font-weight:700;color:#fff;white-space:nowrap}
.badge.high{background:var(--high)}.badge.medium{background:var(--medium)}
.badge.low{background:var(--low)}
.badge.ai-claude{background:var(--claude)}.badge.ai-gemini{background:var(--gemini)}
.badge.ai-codex{background:var(--codex)}
.badge.carry{background:#8250df}
.file{font-family:ui-monospace,monospace;font-size:12px;color:var(--muted)}
.controls{display:flex;gap:16px;padding:0 12px 8px;font-size:13px;color:var(--muted)}
.controls label{cursor:pointer;user-select:none}
.card-body{display:none;border-top:1px solid var(--border);padding:8px 12px}
.card.open .card-body{display:block}
.source{margin:8px 0;padding:8px;border:1px solid var(--border);border-radius:6px}
.source .src-head{font-size:12px;color:var(--muted);margin-bottom:4px}
.source .text{white-space:pre-wrap}
footer{position:fixed;left:0;right:0;bottom:0;background:var(--card);
border-top:1px solid var(--border);padding:10px 16px;display:flex;gap:16px;
align-items:center;flex-wrap:wrap;font-size:13px}
#params{font-family:ui-monospace,monospace}
#save-status{color:var(--muted)}
</style>
</head>
<body>
<h1>AI Review Report</h1>
<div class="meta" id="meta"></div>
<div class="toolbar">
<button id="expand-all">すべて展開</button>
<button id="collapse-all">すべて折りたたむ</button>
<button id="connect-state">状態ファイルを接続</button>
<span id="save-status">未接続(チェック状態は保存されません)</span>
</div>
<div id="report"></div>
<footer>
<span id="progress"></span>
<span id="params"></span>
<button id="copy-params">番号をコピー</button>
</footer>
<script>
const DATA = __REVIEW_DATA__;
const state = {schema_version: 1, items: {}};
let fileHandle = null, saveTimer = null;

const PRIO = [["high","🔴 High Priority"],["medium","🟡 Medium Priority"],["low","🟢 Low Priority"]];
const CARRY = {skipped_before: "前回スキップ", should_be_fixed: "前回対応済のはず"};

function el(tag, cls, text){
  const e = document.createElement(tag);
  if(cls) e.className = cls;
  if(text !== undefined) e.textContent = text;
  return e;
}

function itemState(id){
  const key = String(id);
  if(!state.items[key]) state.items[key] = {reviewed: false, adopt: false};
  return state.items[key];
}

function build(){
  document.getElementById("meta").textContent =
    `PR #${DATA.pr_number} / sources: ${DATA.sources.join(", ")} / items: ${DATA.items.length}`;
  const root = document.getElementById("report");
  root.textContent = "";
  for(const [prio, title] of PRIO){
    const items = DATA.items.filter(i => i.priority === prio);
    if(!items.length) continue;
    root.appendChild(el("h2", "prio-title", title));
    for(const item of items) root.appendChild(card(item));
  }
  if(!DATA.items.length) root.appendChild(el("p", "", "対応が必要な指摘はありません。"));
  refresh();
}

function card(item){
  const c = el("div", "card");
  c.dataset.id = item.id;
  const h = el("div", "card-header");
  h.appendChild(el("span", "", `${item.id}.`));
  h.appendChild(el("span", "badge " + item.priority, item.priority.toUpperCase()));
  for(const s of item.sources)
    h.appendChild(el("span", "badge ai-" + s.ai, s.ai[0].toUpperCase()));
  if(item.carryover)
    h.appendChild(el("span", "badge carry", CARRY[item.carryover] || item.carryover));
  h.appendChild(el("span", "summary", `${item.area}: ${item.summary}`));
  h.appendChild(el("span", "file", `${item.file}:${item.line_spec}`));
  h.addEventListener("click", () => c.classList.toggle("open"));
  c.appendChild(h);

  const ctl = el("div", "controls");
  ctl.appendChild(checkbox(item.id, "reviewed", "確認した"));
  ctl.appendChild(checkbox(item.id, "adopt", "対応する"));
  c.appendChild(ctl);

  const body = el("div", "card-body");
  for(const s of item.sources){
    const box = el("div", "source");
    box.appendChild(el("div", "src-head",
      `${s.ai} #${s.original_number} (影響度: ${s.impact} / 信頼度: ${s.confidence})`));
    box.appendChild(el("div", "text", s.text));
    body.appendChild(box);
  }
  c.appendChild(body);
  return c;
}

function checkbox(id, key, labelText){
  const label = el("label");
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = itemState(id)[key];
  box.addEventListener("click", ev => ev.stopPropagation());
  box.addEventListener("change", () => {
    itemState(id)[key] = box.checked;
    refresh();
    scheduleSave();
  });
  label.appendChild(box);
  label.appendChild(document.createTextNode(" " + labelText));
  label.addEventListener("click", ev => ev.stopPropagation());
  return label;
}

function refresh(){
  let reviewed = 0;
  const adopted = [];
  for(const item of DATA.items){
    const s = itemState(item.id);
    if(s.reviewed) reviewed++;
    if(s.adopt) adopted.push(item.id);
    const c = document.querySelector(`.card[data-id="${item.id}"]`);
    if(c){
      c.classList.toggle("reviewed", s.reviewed);
      c.classList.toggle("adopted", s.adopt);
      const boxes = c.querySelectorAll(".controls input");
      boxes[0].checked = s.reviewed;
      boxes[1].checked = s.adopt;
    }
  }
  document.getElementById("progress").textContent =
    `確認済み ${reviewed}/${DATA.items.length}`;
  document.getElementById("params").textContent =
    adopted.length ? `対応する: ${adopted.join(",")}` : "対応する: (未選択)";
}

async function connectState(){
  try{
    fileHandle = await window.showSaveFilePicker({
      suggestedName: "state.json",
      types: [{description: "JSON", accept: {"application/json": [".json"]}}],
    });
  }catch(e){ return; } // ピッカーのキャンセル
  // 既存stateを選び直したケースは読み込んで復元する
  try{
    const text = await (await fileHandle.getFile()).text();
    if(text.trim()){
      const loaded = JSON.parse(text);
      if(loaded && loaded.items) Object.assign(state.items, loaded.items);
    }
  }catch(e){ /* 新規ファイルや不正JSONは無視して上書き */ }
  refresh();
  await save();
}

function scheduleSave(){
  if(!fileHandle) return;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 300);
}

async function save(){
  if(!fileHandle) return;
  const w = await fileHandle.createWritable();
  await w.write(JSON.stringify(state, null, 1));
  await w.close();
  document.getElementById("save-status").textContent =
    "保存済み " + new Date().toLocaleTimeString();
}

document.getElementById("expand-all").addEventListener("click",
  () => document.querySelectorAll(".card").forEach(c => c.classList.add("open")));
document.getElementById("collapse-all").addEventListener("click",
  () => document.querySelectorAll(".card").forEach(c => c.classList.remove("open")));
document.getElementById("connect-state").addEventListener("click", connectState);
document.getElementById("copy-params").addEventListener("click", () => {
  const ids = DATA.items.filter(i => itemState(i.id).adopt).map(i => i.id).join(",");
  navigator.clipboard.writeText(ids);
});
if(!window.showSaveFilePicker){
  document.getElementById("connect-state").disabled = true;
  document.getElementById("save-status").textContent =
    "このブラウザは状態保存非対応(Chrome系で開いてください)";
}
build();
</script>
</body>
</html>
"""


def render(merged):
    data = json.dumps(merged, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__REVIEW_DATA__", data)


def main(argv):
    if len(argv) != 3:
        print("Usage: generate_review_report.py <merged.json> <output.html>",
              file=sys.stderr)
        return 1
    with open(argv[1], encoding="utf-8") as f:
        merged = json.load(f)
    with open(argv[2], "w", encoding="utf-8") as f:
        f.write(render(merged))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
````

注意: `HTML_TEMPLATE` はPythonの通常文字列なので、テンプレート内に `{}` があってもf-string化しないこと(置換は `__REVIEW_DATA__` の `str.replace` のみ)。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m unittest tests.test_generate_review_report -v`
Expected: 全PASS。

- [ ] **Step 5: setup_ai_pr_tools を *.py 対応にする**

`mac/scripts/common.sh` の `setup_ai_pr_tools` 内、実ディレクトリ分岐のループを変更:

変更前:
```bash
    for file in "${source_dir}"/*.sh; do
```
変更後(common.shはzshでsourceされるため、マッチなしでもエラーにならない `(N)` 修飾子を付ける):
```bash
    for file in "${source_dir}"/*.sh(N) "${source_dir}"/*.py(N); do
```

その後、ライブ環境に反映して確認:

Run: `zsh -c 'source mac/scripts/common.sh && setup_ai_pr_tools' && readlink ~/.config/ai-pr/bin/generate_review_report.py 2>/dev/null; ls ~/.config/ai-pr/bin/`
Expected: `~/.config/ai-pr/bin` がディレクトリごとsymlinkの環境では `generate_review_report.py` がリスト内に見える(個別symlink環境では readlink がリポジトリ内パスを返す)。

- [ ] **Step 6: コミット**

```bash
git add shell/common/pr/generate_review_report.py tests/shell/common/pr/test_generate_review_report.py mac/scripts/common.sh
git commit -m "feat(shell): ✨ レビュー統合HTMLレポート生成を追加"
```

---

### Task 4: レビューコアに結果ファイル書き出しを追加

**Files:**
- Modify: `ai/common/pr_review_core.md`(末尾に追記)
- Modify: `ai/common/pr_review_subagents/orchestrator_core.md`(末尾に追記)
- Regenerate: `ai/codex/skills/pr-review/SKILL.md`, `ai/codex/skills/pr-review-subagents/SKILL.md`

**Interfaces:**
- Produces: 環境変数 `AI_REVIEW_OUTPUT_FILE` が設定されたレビューセッションは、最終出力の完全な複製をそのパスに書き出す(Task 7のウォッチャーがこれを完了シグナルとして待つ)。

- [ ] **Step 1: 両コアに同一セクションを追記**

`ai/common/pr_review_core.md` と `ai/common/pr_review_subagents/orchestrator_core.md` の両方の末尾に、以下のセクションを追加する(英語、そのまま):

```markdown
## Result File Output

Run `printenv AI_REVIEW_OUTPUT_FILE`. If it prints a path: after presenting the final review output, create the parent directory (`mkdir -p`) and write the exact same markdown — from the first line of the review output to the last, with no extra commentary — to that path. Write the file even when the result is `対応が必要な指摘はありません。`. If the variable is unset or empty, skip this section entirely.
```

- [ ] **Step 2: Codexスキルを再生成し冪等性を検証**

Run: `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'`
Expected: exit 0。`git diff --stat` で `ai/codex/skills/pr-review/SKILL.md` と `ai/codex/skills/pr-review-subagents/SKILL.md` のみ変化(追記分)。

- [ ] **Step 3: Geminiはランタイムinclude(`!{cat ...}`)なので再生成不要なことを確認**

Run: `grep -l 'pr_review_core' ai/gemini/commands/*.toml`
Expected: `pr-review.toml`(と subagents)がランタイムincludeであること(catコマンド参照が出る)。出なければGemini側の追従漏れなので構成を確認して報告する。

- [ ] **Step 4: テストスイート実行**

Run: `python3 -m unittest discover -s tests`
Expected: 既存含め全PASS(既知の pre-existing failure があれば従前と同一であること)。

- [ ] **Step 5: コミット**

```bash
git add ai/common/pr_review_core.md ai/common/pr_review_subagents/orchestrator_core.md ai/codex/skills/pr-review/SKILL.md ai/codex/skills/pr-review-subagents/SKILL.md
git commit -m "feat(ai): ✨ レビュー結果のファイル書き出し指示を追加"
```

---

### Task 5: gm-pr-review を yolo 化

**Files:**
- Modify: `shell/zsh/alias/ai/gemini.zsh:47-51`(`gm-pr-review`)

ユーザー承認済みの変更(planモードでは結果ファイルを書き出せないため。`gm-pr-review-subagent` は既にyolo)。

- [ ] **Step 1: 変更**

変更前(gemini.zsh の gm-pr-review 内):
```zsh
    gmh --approval-mode plan -i "/pr-review $pr_number${review_prompt:+ $review_prompt}"
```
変更後:
```zsh
    gmh --approval-mode yolo -i "/pr-review $pr_number${review_prompt:+ $review_prompt}"
```

- [ ] **Step 2: 動作確認**

Run: `zsh -c 'source shell/zsh/alias/ai/gemini.zsh 2>/dev/null; typeset -f gm-pr-review' | grep yolo`
Expected: yolo を含む行が出る。

- [ ] **Step 3: コミット**

```bash
git add shell/zsh/alias/ai/gemini.zsh
git commit -m "fix(gemini): 🐛 gm-pr-reviewをyolo起動にして書き出しを許可"
```

---

### Task 6: review-merge スキル(コア+アダプタ+ラッパー)

**Files:**
- Create: `ai/common/review_merge_core.md`
- Create: `ai/claude/skills/review-merge/SKILL.md`
- Create: `ai/codex/skills/review-merge/skill_head.md`(SKILL.mdは生成)
- Modify: `mac/scripts/common.sh` の `generate_codex_skills` にエントリ追加
- Modify: `shell/common/alias/claude.sh`(`cl-review-merge`)
- Modify: `shell/zsh/alias/ai/codex.zsh`(`cx-review-merge`)

**Interfaces:**
- Consumes: ランディレクトリの `{claude,gemini,codex}.md`(Task 4の書き出し)、`ai_review_run_dir.sh --latest`(Task 1)、`generate_review_report.py`(Task 3)
- Produces: `<RUN_DIR>/merged.json`(スキーマ下記)と `<RUN_DIR>/report.html`。シェル関数 `cl-review-merge <run_dir>`(Task 7が呼ぶ)。

- [ ] **Step 1: 共有コアを作成**

`ai/common/review_merge_core.md`(全文):

````markdown
Merge the per-AI PR review result files in <RUN_DIR> into `merged.json` and generate `report.html`. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `claude.md` / `gemini.md` / `codex.md` (any subset). If none exists, stop and report the directory path.
- Each file follows the pr-review output format: numbered findings with a header line `N. **[path:line]** 領域 (影響度: XX / 信頼度: XX): summary`, an indented detail bullet, and a `---` separator, grouped under priority sections.

## Workflow

1. Read every existing result file. Parse each finding: original number, file path, line spec, 領域, 影響度, 信頼度, priority section, summary, detail text. Ignore `## [既コメント済] スキップした指摘` and `## 総合評価` sections.
2. Merge findings that point at the same root cause (same file and same/overlapping lines, or clearly the same issue in meaning even if line numbers differ slightly). Never drop any source text: a merged item keeps every AI's original finding verbatim in `sources`.
3. For each merged item set: `file` and `line_spec` from the most confident source, `area` from the most confident source, `priority` = highest among sources (high > medium > low; section headings map 🔴→high, 🟡→medium, 🟢→low), and write a one-sentence Japanese `summary` for the merged item yourself.
4. Number items sequentially (`id` starting at 1), ordered high → medium → low.
5. Carryover: resolve the previous run — the newest sibling run directory of <RUN_DIR> (same parent) that contains `merged.json`, excluding <RUN_DIR> itself. If found, read its `merged.json` and `state.json` (if present). For each new item that matches a previous item (same file and same root cause):
   - previous state `adopt: false` (or unset) → `"carryover": "skipped_before"`
   - previous state `adopt: true` → `"carryover": "should_be_fixed"`
   No previous run, no state, or no match → `"carryover": null`.
6. Record the current PR head: `gh pr view <PR_NUMBER> --json headRefOid --jq .headRefOid` (PR number from the run directory path `pr-<N>`), stored as `head_ref_oid`.
7. Write `<RUN_DIR>/merged.json` (schema below), then render and open the report:

```bash
python3 ~/.config/ai-pr/bin/generate_review_report.py <RUN_DIR>/merged.json <RUN_DIR>/report.html
open -a "Google Chrome" <RUN_DIR>/report.html
```

8. Print a Japanese summary: per-AI finding counts, merged item count, how many duplicates were merged, carryover counts, and the follow-up usage — check items in the browser (状態ファイルを接続 → save state.json into <RUN_DIR>), then run `review-post` (PRコメント投稿) or `review-fix` (修正) with <RUN_DIR>.

## merged.json schema

```json
{
  "schema_version": 1,
  "pr_number": 123,
  "head_ref_oid": "<sha>",
  "run_dir": "/abs/path/to/run",
  "sources": ["claude", "codex"],
  "items": [
    {
      "id": 1,
      "file": "src/auth.ts",
      "line_spec": "42",
      "area": "セキュリティ",
      "priority": "high",
      "summary": "merged one-line Japanese summary",
      "carryover": null,
      "sources": [
        {"ai": "claude", "original_number": 4, "priority": "high",
         "impact": "High", "confidence": 85, "text": "original detail text"}
      ]
    }
  ]
}
```

`line_spec` keeps the original notation (`42`, `42-50`, `~42`). `carryover` is `null` / `"skipped_before"` / `"should_be_fixed"`.
````

- [ ] **Step 2: Claudeアダプタを作成**

`ai/claude/skills/review-merge/SKILL.md`(全文。既存 `ai/claude/skills/pr-review/SKILL.md` のfrontmatter流儀に合わせる):

```markdown
---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(python3:*), Bash(open:*), Bash(printenv:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Write, Glob
description: "Merge multi-AI PR review result files into merged.json and an HTML report"
argument-hint: "[runDir]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

!`/bin/cat ~/.claude/common/review_merge_core.md`
```

- [ ] **Step 3: Codexアダプタを作成し生成に登録**

`ai/codex/skills/review-merge/skill_head.md`(全文。frontmatterは既存Codexスキルの最小構成に合わせ、実物の `ai/codex/skills/pr-review/skill_head.md` を見て体裁を揃える):

```markdown
---
name: review-merge
description: Merge multi-AI PR review result files into merged.json and an HTML report
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.
```

`mac/scripts/common.sh` の `generate_codex_skills` のエントリリストに追加(fact-based行の前に):

```zsh
    "review-merge:review_merge_core.md" \
```

- [ ] **Step 4: 再生成+冪等性検証**

Run: `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'`
Expected: exit 0。`ai/codex/skills/review-merge/SKILL.md` が生成される。

- [ ] **Step 5: 起動ラッパーを追加**

`shell/common/alias/claude.sh` に追加(`cl-pr-review-subagents` の後):

```bash
cl-review-merge() {
    local run_dir="$1"
    if [[ -z "$run_dir" ]]; then
        echo "Usage: cl-review-merge <run_dir>" >&2
        return 1
    fi
    clf --effort high --dangerously-skip-permissions "/review-merge $run_dir"
}
```

`shell/zsh/alias/ai/codex.zsh` に追加(`cx-pr-review-subagent` の後、救済用の手動代替):

```zsh
cx-review-merge() {
    local run_dir="$1"
    if [[ -z "$run_dir" ]]; then
        echo "Usage: cx-review-merge <run_dir>" >&2
        return 1
    fi
    cxh --dangerously-bypass-approvals-and-sandbox "\$review-merge $run_dir"
}
```

- [ ] **Step 6: スキルのライブ反映と確認**

Claudeスキルはディレクトリ単位symlinkで自動配備される。`mac/initialization/ai/claude.sh` の `setup_ai_skills` 呼び出し(引数はそのファイルの実物を確認)と同じ形で実行し、`readlink ~/.claude/skills/review-merge` がリポジトリ内を指すことを確認。Codex側も同様に `~/.codex/skills/review-merge` を確認。

- [ ] **Step 7: テストスイート実行**

Run: `python3 -m unittest discover -s tests`
Expected: 全PASS(従前の既知failureを除く)。

- [ ] **Step 8: コミット**

```bash
git add ai/common/review_merge_core.md ai/claude/skills/review-merge ai/codex/skills/review-merge mac/scripts/common.sh shell/common/alias/claude.sh shell/zsh/alias/ai/codex.zsh
git commit -m "feat(ai): ✨ review-mergeスキルを追加"
```

---

### Task 7: ランチャー自動チェーン化と review-all 削除

**Files:**
- Modify: `shell/zsh/alias/ai/ai.zsh`(305-485行の review 系を置換)
- Test: `tests/shell/zsh/alias/ai/test_ai_zsh__ai_review_launcher.py`

**Interfaces:**
- Consumes: `ai_review_run_dir.sh`(Task 1)、`ai_review_wait.sh`(Task 2)、`cl-review-merge`(Task 6)、既存 `cl-pr-review`/`gm-pr-review`/`cx-pr-review`(+subagents変種。codexは単数形 `cx-pr-review-subagent` なことに注意)
- Produces: `review [--no-merge] [pr] [prompt...]` / `review-subagents [--no-merge] [pr] [prompt...]` / `review-merge [pr]`。`review-all` と `_review_all_tmux` / `_review_all_herdr` は削除。

- [ ] **Step 1: 失敗するテストを書く**

`tests/shell/zsh/alias/ai/test_ai_zsh__ai_review_launcher.py`(zsh関数の純粋部分のみ検証):

```python
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_ZSH = REPO_ROOT / "shell" / "zsh" / "alias" / "ai" / "ai.zsh"


def run_zsh(snippet):
    return subprocess.run(
        ["zsh", "-c", f'SET="{REPO_ROOT}"; source "{AI_ZSH}"; {snippet}'],
        capture_output=True, text=True,
    )


class AiReviewLauncherTest(unittest.TestCase):
    def test_env_command_prefixes_output_file(self):
        result = run_zsh(
            "_ai_review_env_command /tmp/run/claude.md cl-pr-review 123 'extra note'"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # zshの ${(q)} はスペースをバックスラッシュでクォートする
        self.assertEqual(
            result.stdout.strip(),
            "AI_REVIEW_OUTPUT_FILE=/tmp/run/claude.md cl-pr-review 123 extra\\ note",
        )

    def test_env_tmux_command_appends_shell(self):
        result = run_zsh("_ai_review_env_tmux_command /tmp/run/codex.md cx-pr-review 9")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith("; zsh"))

    def test_review_all_removed(self):
        for name in ("review-all", "_review_all_tmux", "_review_all_herdr"):
            with self.subTest(name=name):
                result = run_zsh(f"typeset -f -- {name} >/dev/null")
                self.assertNotEqual(result.returncode, 0)

    def test_review_functions_exist(self):
        for name in ("review", "review-subagents", "review-merge", "_review_run"):
            with self.subTest(name=name):
                result = run_zsh(f"typeset -f -- {name} >/dev/null")
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m unittest tests.test_ai_review_launcher -v`
Expected: `test_env_command_prefixes_output_file` / `test_review_all_removed` などがFAIL。

- [ ] **Step 3: ai.zsh を書き換える**

(a) `_ai_review_tmux_command` の直後に追加:

```zsh
# レビュー結果の書き出し先(AI_REVIEW_OUTPUT_FILE)を前置した起動コマンドを返す
_ai_review_env_command() {
    local output_file="$1"
    shift
    print -r -- "AI_REVIEW_OUTPUT_FILE=${(q)output_file} $(_ai_review_command "$@")"
}

# tmux new-window用: コマンド実行後もwindowにシェルを残すため "; zsh" を付与
_ai_review_env_tmux_command() {
    print -r -- "$(_ai_review_env_command "$@"); zsh"
}
```

(b) `_review_tmux` / `_review_herdr` / `_review_subagents_tmux` / `_review_subagents_herdr` / `_review_all_tmux` / `_review_all_herdr` / `review()` / `review-subagents()` / `review-all()` を全て削除し、以下で置換:

```zsh
# 3AIをそれぞれreview workspaceの新規タブで起動する（herdr）
# 引数: run_dir claude_fn gemini_fn codex_fn review_args...
_review_launch_herdr() {
    local run_dir="$1" claude_fn="$2" gemini_fn="$3" codex_fn="$4"
    shift 4
    local -a review_args=("$@")

    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    local ws_id claude_label gemini_label codex_label
    local claude_command gemini_command codex_command
    # ラベル計算（git名依存）を先に行い、失敗時は無駄なworkspace作成/流用探索を避ける
    claude_label=$(_ai_review_herdr_label "${EMOJI_ID_CLAUDE}") || return 1
    gemini_label=$(_ai_review_herdr_label "${EMOJI_ID_GEMINI}") || return 1
    codex_label=$(_ai_review_herdr_label "${EMOJI_ID_CODEX}") || return 1
    ws_id=$(_herdr_resolve_review_workspace "${PWD}") || return 1
    claude_command=$(_ai_review_env_command "${run_dir}/claude.md" "${claude_fn}" "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_env_command "${run_dir}/gemini.md" "${gemini_fn}" "${review_args[@]}") || return 1
    codex_command=$(_ai_review_env_command "${run_dir}/codex.md" "${codex_fn}" "${review_args[@]}") || return 1

    # Claudeも新規タブで起動する（元タブはウォッチャー→review-mergeに使う）
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${claude_label}" "${claude_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${gemini_label}" "${gemini_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${codex_label}" "${codex_command}" || return 1

    herdr workspace focus "${ws_id}" >/dev/null 2>&1
}

# 3AIをそれぞれ新規ウィンドウで起動する（tmux）
# 引数: run_dir claude_fn gemini_fn codex_fn review_args...
_review_launch_tmux() {
    local run_dir="$1" claude_fn="$2" gemini_fn="$3" codex_fn="$4"
    shift 4
    local -a review_args=("$@")

    local review_name claude_command gemini_command codex_command
    review_name=$(_review_window_name)
    claude_command=$(_ai_review_env_tmux_command "${run_dir}/claude.md" "${claude_fn}" "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_env_tmux_command "${run_dir}/gemini.md" "${gemini_fn}" "${review_args[@]}") || return 1
    codex_command=$(_ai_review_env_tmux_command "${run_dir}/codex.md" "${codex_fn}" "${review_args[@]}") || return 1

    # ウォッチャーをカレントウィンドウで動かすため、3AIとも -d（非フォーカス）で起動する
    tmux new-window -d -n "${review_name}" "zsh -ic ${(q)claude_command}" || return 1
    tmux new-window -d -n "${review_name}" "zsh -ic ${(q)gemini_command}" || return 1
    tmux new-window -d -n "${review_name}" "zsh -ic ${(q)codex_command}" || return 1

    # カレントウィンドウは共有実装で🔍を付与（_review_window_name が git 名へ改名済み）
    _ai_ensure_window_name_helper
    update_tmux_window_name "${EMOJI_STATUS_REVIEW}"
}

# レビューの共通フロー: ランディレクトリ作成 → 3AI起動 → 完了待ち → review-merge
# 引数: claude_fn gemini_fn codex_fn [--no-merge] [pr] [prompt...]
_review_run() {
    local claude_fn="$1" gemini_fn="$2" codex_fn="$3"
    shift 3

    local no_merge=0
    if [[ "${1:-}" == "--no-merge" ]]; then
        no_merge=1
        shift
    fi

    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local -a review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    local run_dir
    run_dir=$(bash "$HOME/.config/ai-pr/bin/ai_review_run_dir.sh" "${pr_number}") || return 1

    case "$(_ai_multiplexer_kind)" in
        herdr) _review_launch_herdr "${run_dir}" "${claude_fn}" "${gemini_fn}" "${codex_fn}" "${review_args[@]}" || return 1 ;;
        tmux) _review_launch_tmux "${run_dir}" "${claude_fn}" "${gemini_fn}" "${codex_fn}" "${review_args[@]}" || return 1 ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac

    if (( no_merge )); then
        echo "レビューを起動しました（自動マージなし）: ${run_dir}"
        return 0
    fi

    bash "$HOME/.config/ai-pr/bin/ai_review_wait.sh" "${run_dir}" claude.md gemini.md codex.md || return $?
    cl-review-merge "${run_dir}"
}

review() {
    _review_run cl-pr-review gm-pr-review cx-pr-review "$@"
}

review-subagents() {
    _review_run cl-pr-review-subagents gm-pr-review-subagent cx-pr-review-subagent "$@"
}

# 手動マージ（救済用）: 最新ランディレクトリを解決して review-merge スキルを起動する
review-merge() {
    local pr_number
    if [[ $# -gt 0 ]] && _ai_pr_review_arg_is_pr_ref "$1"; then
        pr_number="${1#\#}"
        shift
    else
        pr_number=$(gh pr view --json number --jq .number) || {
            echo "現在のブランチに対応するPRが見つかりません。" >&2
            return 1
        }
    fi

    local run_dir
    run_dir=$(bash "$HOME/.config/ai-pr/bin/ai_review_run_dir.sh" --latest "${pr_number}") || return 1
    cl-review-merge "${run_dir}"
}
```

(c) 未使用になったヘルパーの整理: `grep -rn '_ai_review_tmux_command\|_review_window_name' shell/ ai/ tests/` を実行し、`_ai_review_tmux_command` がai.zsh内でしか使われていなければ削除(`_ai_review_env_tmux_command` が後継)。`_review_window_name` は `_review_launch_tmux` が使い続けるので残す。

(d) `review-all` の残参照の掃除: `grep -rn 'review-all\|review_all' shell/ ai/ CLAUDE.md .claude/ tests/` を実行し、ヒットした参照(filter系エイリアス等)があれば削除する。docs/ 配下のスペック・プランは除外してよい。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m unittest tests.test_ai_review_launcher -v`
Expected: 全PASS。

- [ ] **Step 5: 全体スイート実行**

Run: `python3 -m unittest discover -s tests`
Expected: 全PASS(従前の既知failureを除く)。

- [ ] **Step 6: コミット**

```bash
git add shell/zsh/alias/ai/ai.zsh tests/shell/zsh/alias/ai/test_ai_zsh__ai_review_launcher.py
git commit -m "feat(shell): ✨ reviewコマンドに自動マージチェーンを追加"
```

(c)(d)で他ファイルに削除が及んだ場合は同コミットに含める。

---

### Task 8: 投稿メカニクスの共有コア分離

**Files:**
- Create: `ai/common/pr_post_mechanics_core.md`
- Modify: `ai/common/pr_comment_post_core.md`
- Modify: `ai/claude/skills/pr-comment-post/SKILL.md`
- Modify: `ai/gemini/commands/pr-comment-post.toml`
- Modify: `mac/scripts/common.sh`(`generate_codex_skills` の pr-comment-post エントリ)
- Modify: `CLAUDE.md`(スキル構成表の pr-comment-post 行)
- Regenerate: `ai/codex/skills/pr-comment-post/SKILL.md`

**Interfaces:**
- Produces: `ai/common/pr_post_mechanics_core.md` — PR投稿の共通メカニクス(メタデータ取得、head移動時の再アンカー、プレビュー+確認、Review API投稿、改行安全性)。pr-comment-post と review-post(Task 9)の両方が selection コアの後ろに連結して使う。

- [ ] **Step 1: 分離を実施**

`ai/common/pr_comment_post_core.md` を読み、以下のセクションを**そのままの文面で** `ai/common/pr_post_mechanics_core.md` へ移動する:

- `## Workflow` のステップ4(PRメタデータ取得 `gh pr view --json number,headRefOid` ...)とステップ5(headRefOid差分時の再アンカー)— 新ファイルでは `## PR Metadata And Re-Anchoring` の見出し下でステップ1,2に付番し直す
- `## Preview And Confirm` 全体
- `## Posting` 全体(`### Newline Safety` を含む)

移動後の `pr_comment_post_core.md` に残るのは: Goal、Workflowステップ1〜3(インデックス構築・ITEM_NUMBERSパース・項目転記)。末尾に1行追加: `Then follow the posting mechanics below.`

移動した `## Preview And Confirm` 内の文言 `the original `pr-review` output` は、selection側が何であっても成り立つよう `the source list this skill built its index from` に一般化する。同様に再アンカー文中の `pr-review` 固有表現があれば「the review result this index was built from」に一般化する。それ以外は一字一句変えない。

- [ ] **Step 2: 3プラットフォームの合成を更新**

- `ai/claude/skills/pr-comment-post/SKILL.md`: 既存の `` !`/bin/cat ~/.claude/common/pr_comment_post_core.md` `` 行の直後に `` !`/bin/cat ~/.claude/common/pr_post_mechanics_core.md` `` を追加。
- `ai/gemini/commands/pr-comment-post.toml`: 既存の `!{cat ~/.gemini/common/pr_comment_post_core.md}` の直後に `!{cat ~/.gemini/common/pr_post_mechanics_core.md}` を追加。
- `mac/scripts/common.sh`: `"pr-comment-post:pr_comment_post_core.md"` → `"pr-comment-post:pr_comment_post_core.md pr_post_mechanics_core.md"`。

- [ ] **Step 3: 再生成+冪等性検証**

Run: `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'`
Expected: exit 0。生成後の `ai/codex/skills/pr-comment-post/SKILL.md` の内容が分離前と意味的に同一(セクション順序が保たれている)ことを `git diff` で目視確認。

- [ ] **Step 4: CLAUDE.md の表を更新**

スキル構成表の pr-comment-post 行を `pr_comment_post_core.md` + `pr_post_mechanics_core.md` に更新(同一コミットで)。

- [ ] **Step 5: コミット**

```bash
git add ai/common/pr_comment_post_core.md ai/common/pr_post_mechanics_core.md ai/claude/skills/pr-comment-post/SKILL.md ai/gemini/commands/pr-comment-post.toml ai/codex/skills/pr-comment-post/SKILL.md mac/scripts/common.sh CLAUDE.md
git commit -m "refactor(ai): ♻️ PR投稿メカニクスを共有コアへ分離"
```

---

### Task 9: review-post スキル

**Files:**
- Create: `ai/common/review_post_core.md`
- Create: `ai/claude/skills/review-post/SKILL.md`
- Create: `ai/codex/skills/review-post/skill_head.md`(SKILL.mdは生成)
- Modify: `mac/scripts/common.sh`(生成エントリ)
- Modify: `shell/common/alias/claude.sh`(`cl-review-post`)、`shell/zsh/alias/ai/codex.zsh`(`cx-review-post`)

**Interfaces:**
- Consumes: `merged.json` / `state.json`(Task 6のスキーマ)、`pr_post_mechanics_core.md`(Task 8)
- Produces: スキル `review-post`(Claude/Codex) — 採用項目をPRにレビューコメント投稿。

- [ ] **Step 1: 共有コアを作成**

`ai/common/review_post_core.md`(全文):

```markdown
Post selected review items from a merge run directory to the PR as review comments. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items (`id. [file:line_spec] priority | area: summary`) and ask the user which ids to post.
3. If a selected id has no matching item, or state.json ids do not exist in merged.json (stale state), stop and report the mismatch instead of guessing.
4. Build the posting index from the selected items: `N. [file:line_spec] Priority | 領域: 概要` where `N` = item id, Priority from `priority` (high→High, medium→Medium, low→Low), 領域 from `area`, 概要 from `summary`. The posted description body is: the merged `summary`, a blank line, then the detail `text` of the most confident source; if the item has multiple sources, append a final line `（同指摘: <other AI names>）`.
5. `head_ref_oid` in merged.json is the review-time head commit for the re-anchoring check in the posting mechanics below. Items whose `line_spec` starts with `~` are pre-existing-code anchors and cannot be inline comments (see the fallback rule in the mechanics).

Then follow the posting mechanics below.
```

- [ ] **Step 2: Claudeアダプタを作成**

`ai/claude/skills/review-post/SKILL.md`(全文):

```markdown
---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Glob
description: "Post adopted review items from a merge run directory as PR review comments"
argument-hint: "[runDir] [itemNumbers...]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For the final posting confirmation, use the AskUserQuestion tool.

!`/bin/cat ~/.claude/common/review_post_core.md`

!`/bin/cat ~/.claude/common/pr_post_mechanics_core.md`
```

- [ ] **Step 3: Codexアダプタ+生成エントリ**

`ai/codex/skills/review-post/skill_head.md`(全文):

```markdown
---
name: review-post
description: Post adopted review items from a merge run directory as PR review comments
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For the final posting confirmation, ask the user directly and wait for the reply.
```

`generate_codex_skills` に追加:

```zsh
    "review-post:review_post_core.md pr_post_mechanics_core.md" \
```

- [ ] **Step 4: 起動ラッパー**

`shell/common/alias/claude.sh`:

```bash
cl-review-post() {
    clo --dangerously-skip-permissions "/review-post $*"
}
```

`shell/zsh/alias/ai/codex.zsh`:

```zsh
cx-review-post() {
    cxh --dangerously-bypass-approvals-and-sandbox "\$review-post $*"
}
```

- [ ] **Step 5: 再生成+冪等性検証+スイート**

Run: `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'` → exit 0
Run: `python3 -m unittest discover -s tests` → 全PASS

- [ ] **Step 6: コミット**

```bash
git add ai/common/review_post_core.md ai/claude/skills/review-post ai/codex/skills/review-post mac/scripts/common.sh shell/common/alias/claude.sh shell/zsh/alias/ai/codex.zsh
git commit -m "feat(ai): ✨ review-postスキルを追加"
```

---

### Task 10: review-fix スキル

**Files:**
- Create: `ai/common/review_fix_core.md`
- Create: `ai/claude/skills/review-fix/SKILL.md`
- Create: `ai/codex/skills/review-fix/skill_head.md`(SKILL.mdは生成)
- Modify: `mac/scripts/common.sh`(生成エントリ)
- Modify: `shell/common/alias/claude.sh`(`cl-review-fix`)、`shell/zsh/alias/ai/codex.zsh`(`cx-review-fix`)

**Interfaces:**
- Consumes: `merged.json` / `state.json`(Task 6のスキーマ)
- Produces: スキル `review-fix`(Claude/Codex) — 採用項目をワーキングツリーで修正。

- [ ] **Step 1: 共有コアを作成**

`ai/common/review_fix_core.md`(全文):

```markdown
Fix selected review items from a merge run directory in the current working tree. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items and ask the user which ids to fix.
3. If a selected id has no matching item, stop and report the mismatch instead of guessing.

## Workflow

1. Present the selected items (`id. [file:line_spec] priority | area: summary`) and confirm with the user before editing anything.
2. Fix the items one by one. For each item: read the file and enough surrounding context, use every source's detail text as guidance, apply the fix. If the finding looks wrong, already fixed, or the fix is genuinely ambiguous, skip it and record the reason — never guess.
3. After all items, run the repository's relevant tests (follow the project's documented test command).
4. Final summary in Japanese: per item — 修正済み (what changed, files touched) or スキップ (why); then `git diff --stat` output. Do not commit — leave the commit decision to the session's normal workflow.
```

- [ ] **Step 2: Claudeアダプタ**

`ai/claude/skills/review-fix/SKILL.md`(全文):

```markdown
---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Edit, Write, Glob, Grep
description: "Fix adopted review items from a merge run directory in the working tree"
argument-hint: "[runDir] [itemNumbers...]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For the pre-edit confirmation, use the AskUserQuestion tool.

!`/bin/cat ~/.claude/common/review_fix_core.md`
```

- [ ] **Step 3: Codexアダプタ+生成エントリ**

`ai/codex/skills/review-fix/skill_head.md`(全文):

```markdown
---
name: review-fix
description: Fix adopted review items from a merge run directory in the working tree
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For the pre-edit confirmation, ask the user directly and wait for the reply.
```

`generate_codex_skills` に追加:

```zsh
    "review-fix:review_fix_core.md" \
```

- [ ] **Step 4: 起動ラッパー**

`shell/common/alias/claude.sh`:

```bash
cl-review-fix() {
    clf --effort high "/review-fix $*"
}
```

`shell/zsh/alias/ai/codex.zsh`:

```zsh
cx-review-fix() {
    cxh "\$review-fix $*"
}
```

(review-fixはコードを書き換えるため、投稿系と違い権限スキップを付けず通常の確認フローに任せる。)

- [ ] **Step 5: 再生成+冪等性検証+スイート**

Run: `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'` → exit 0
Run: `python3 -m unittest discover -s tests` → 全PASS

- [ ] **Step 6: コミット**

```bash
git add ai/common/review_fix_core.md ai/claude/skills/review-fix ai/codex/skills/review-fix mac/scripts/common.sh shell/common/alias/claude.sh shell/zsh/alias/ai/codex.zsh
git commit -m "feat(ai): ✨ review-fixスキルを追加"
```

---

### Task 11: ドキュメント更新

**Files:**
- Modify: `CLAUDE.md`(スキル構成表に3行追加)
- Commit: `docs/superpowers/specs/2026-07-26-ai-review-merge-flow-design.md`、`docs/superpowers/plans/2026-07-26-ai-review-merge-flow.md`(未コミットなら)

- [ ] **Step 1: CLAUDE.md のスキル構成表に追加**

共有コアスキルの表(pr-review等が載っている表)に3行追加:

```markdown
| review-merge | `review_merge_core.md` | Claude and Codex only; adapter-head bits: `RUN_DIR` resolution, confirmation primitive |
| review-post | `review_post_core.md` + `pr_post_mechanics_core.md` | Claude and Codex only; adapter-head bits: `RUN_DIR`/`ITEM_NUMBERS`, confirmation primitive |
| review-fix | `review_fix_core.md` | Claude and Codex only; adapter-head bits: `RUN_DIR`/`ITEM_NUMBERS`, confirmation primitive |
```

(pr-comment-post行の更新はTask 8で実施済み。)

- [ ] **Step 2: コミット**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-07-26-ai-review-merge-flow-design.md docs/superpowers/plans/2026-07-26-ai-review-merge-flow.md
git commit -m "docs(ai): 📝 レビュー統合フローの構成と設計文書を追加"
```

---

### Task 12: 検証(全体スイート+手動E2Eチェックリスト)

- [ ] **Step 1: 全体テストスイート**

Run: `python3 -m unittest discover -s tests`
Expected: 全PASS(着手前から存在する既知failureがあれば、それと同一集合であること)。

- [ ] **Step 2: 生成物の最終冪等性検証**

Run: `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'`
Expected: exit 0、`git status` がclean(生成物のstale無し)。

- [ ] **Step 3: 手動E2E(ユーザーと実施)**

自動化不能な箇所のチェックリスト。実PRを使う(herdr内で実行):

1. `review <PR番号>` → 3タブ(C/G/X)がreview workspaceに立ち、元タブに進捗表示(`claude … / gemini … / codex …`)が出る
2. 各AIの完了と同時に対応する `✓` が進む。全完了で元タブが review-merge に遷移
3. Chrome で report.html が開く。カード折り畳み、確認/対応チェック、フッターの番号表示が動く
4. 「状態ファイルを接続」→ ランディレクトリの `state.json` を選択 → チェックのたび保存済み表示が更新される(**file://でのFile System Access API可否の確認ポイント**。ブロックされる場合はフッターの番号コピーで代替し、要改善として報告)
5. `cl-review-fix <run_dir>`(または引数なし)で採用項目の一覧が出て、確認後に修正される
6. 他人PR相当の流れとして `cl-review-post <run_dir>` で投稿プレビュー→確認→投稿(テストは自分のPRでよい)
7. 同じPRでもう一度 `review` を回し、2回目のレポートに「前回スキップ」「前回対応済のはず」バッジが出る
8. `review --no-merge` でウォッチャーが走らないこと、`review-merge` 手動起動で救済できること

---

## Self-Review メモ(プラン作成時に確認済み)

- スペックの全要件とタスクの対応: 書き出し(T4)、ランディレクトリ+latest+保持(T1)、ウォッチャー+自動チェーン+Claude新タブ化+--no-merge(T2,T7)、review-all削除(T7)、マージ+原文保持+ラウンド間引き継ぎ+head記録(T6)、レンダリング+バッジ+FSA保存+フッター(T3)、review-post(T8,T9)、review-fix(T10)、Gemini yolo(T5)、CLAUDE.md表(T8,T11)、テスト(T1,T2,T3,T7,T12)。
- 型整合: `merged.json`/`state.json` スキーマはT3(レンダラ/テスト)・T6(コア定義)・T9/T10(読み取り)で同一形(`items` はidキーのオブジェクト、`carryover` は null/skipped_before/should_be_fixed)。
- 名前整合: `cl-review-merge`/`cx-review-merge`(T6) を T7 が呼ぶ。`ai_review_run_dir.sh --latest`(T1)を T6/T9/T10 アダプタと T7 `review-merge` が呼ぶ。codexのsubagent関数は単数形 `cx-pr-review-subagent`。
