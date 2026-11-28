#!/bin/bash
# freviewが作ったレビュー用一時worktreeを、安全確認のうえ削除する。
# 使い方: ai_review_cleanup_worktree.sh <run_dir>
#
# run_dir/temp_worktree（1行目=worktreeパス, 2行目=このフローで新規作成したブランチ名。空なら既存ブランチ）
# を読む。ファイルが無ければ何もしない。次の場合はworktreeを残して理由を表示する（exit 0）:
#   - 未コミットの変更（未追跡ファイル含む）がある
#   - どのremoteにも無いコミットがある（レビュー中に修正を積んだがpush前など）
# worktree削除に成功したら、新規作成ブランチもremote未反映コミットが無い場合に限って削除する
# （PRブランチはmain未マージのため通常の -d では消せず、-D を条件付きで使う）。
# 削除に成功したらtemp_worktreeを消す。--forceは使わない。

set -u

run_dir="${1:-}"
if [[ -z "$run_dir" ]]; then
    echo "使い方: ai_review_cleanup_worktree.sh <run_dir>" >&2
    exit 2
fi

marker="${run_dir}/temp_worktree"
[[ -f "$marker" ]] || exit 0

worktree_path=$(sed -n 1p "$marker")
branch=$(sed -n 2p "$marker")

if [[ -z "$worktree_path" ]]; then
    echo "temp_worktreeにworktreeパスがありません: ${marker}" >&2
    exit 1
fi

if [[ ! -d "$worktree_path" ]]; then
    echo "一時worktreeは既に削除されています: ${worktree_path}"
    rm -f "$marker"
    exit 0
fi

# 先頭エントリがメインworktree。削除コマンドの実行元にし、削除対象としては拒否する
main_worktree=$(git -C "$worktree_path" worktree list --porcelain 2>/dev/null | sed -n '1s/^worktree //p')
if [[ -z "$main_worktree" ]]; then
    echo "worktree一覧を取得できませんでした: ${worktree_path}" >&2
    exit 1
fi
if [[ "$(cd "$worktree_path" && pwd -P)" == "$(cd "$main_worktree" && pwd -P)" ]]; then
    echo "メインworktreeは削除しません: ${worktree_path}" >&2
    exit 1
fi

if [[ -n "$(git -C "$worktree_path" status --porcelain 2>/dev/null)" ]]; then
    echo "未コミットの変更があるため一時worktreeを残しました: ${worktree_path}"
    exit 0
fi

if [[ -n "$(git -C "$worktree_path" rev-list HEAD --not --remotes 2>/dev/null)" ]]; then
    echo "pushされていないコミットがあるため一時worktreeを残しました: ${worktree_path}"
    exit 0
fi

if ! git -C "$main_worktree" worktree remove "$worktree_path"; then
    echo "一時worktreeの削除に失敗しました: ${worktree_path}" >&2
    exit 1
fi
rm -f "$marker"
echo "一時worktreeを削除しました: ${worktree_path}"

if [[ -n "$branch" ]] && git -C "$main_worktree" show-ref --verify --quiet "refs/heads/${branch}"; then
    if [[ -n "$(git -C "$main_worktree" rev-list "refs/heads/${branch}" --not --remotes 2>/dev/null)" ]]; then
        echo "pushされていないコミットがあるためブランチを残しました: ${branch}"
    elif git -C "$main_worktree" branch -D "$branch" >/dev/null; then
        echo "ブランチを削除しました: ${branch}"
    else
        echo "ブランチの削除に失敗しました: ${branch}" >&2
        exit 1
    fi
fi
exit 0
