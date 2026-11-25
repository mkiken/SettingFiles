#!/bin/zsh
# Herdr Spacesサイドバーに現ブランチのPR番号を出すためのprecmdフック。
#
# 組み込みトークンにPRは無いため、`gh pr view`で調べた番号を
# `herdr workspace report-metadata`の`pr`トークン（config.tomlで`$pr`として表示）に書く。
# gh呼び出しはプロンプトを止めないようバックグラウンドで行い、同一リポジトリ・
# ブランチへの再照会はTTL内なら省く（PR作成後に出るよう、TTL経過で再照会する）。
#
# 既知の制限: 更新はシェルがプロンプトを出した時だけ。AIがペイン内でcheckoutしても
# 次のプロンプトまで反映されず、同一workspaceの複数ペインは最後に動いたものが勝つ。

_HERDR_SPACE_PR_TTL=300
typeset -g _herdr_space_pr_key=""
typeset -gi _herdr_space_pr_checked_at=-1

# PR番号を調べてworkspaceのprトークンへ反映する。PRが無い・ghが失敗した場合は
# 古い番号が残らないようトークンを消す。
# Usage: _herdr_space_pr_report <workspace_id> <toplevel> <branch>
function _herdr_space_pr_report() {
  local workspace_id="$1" toplevel="$2" branch="$3"
  local herdr_bin="${HERDR_BIN_PATH:-herdr}"
  local number=""

  if [[ -n "$toplevel" && -n "$branch" ]]; then
    number=$(builtin cd -q -- "$toplevel" 2>/dev/null && command gh pr view "$branch" --json number -q .number 2>/dev/null)
  fi

  if [[ "$number" == <-> ]]; then
    "$herdr_bin" workspace report-metadata "$workspace_id" --source space-pr --token "pr=#${number}" >/dev/null 2>&1
  else
    "$herdr_bin" workspace report-metadata "$workspace_id" --source space-pr --clear-token pr >/dev/null 2>&1
  fi
}

function _herdr_space_pr_precmd() {
  # tmuxとHerdrは排他。Herdr外では何もしない
  [[ -n "${HERDR_WORKSPACE_ID:-}" && -z "${TMUX:-}" ]] || return 0

  local out toplevel branch key
  local -a lines
  # 1回のgitでtoplevelとブランチを得る。repo外では失敗して空になる
  out=$(command git rev-parse --show-toplevel --symbolic-full-name HEAD 2>/dev/null)
  lines=("${(@f)out}")
  toplevel="${lines[1]}"
  branch="${lines[2]#refs/heads/}"
  # detached HEADは`HEAD`と出る。ブランチ無し扱いにする
  [[ "$branch" == HEAD ]] && branch=""

  key="${toplevel}:${branch}"
  if [[ "$key" == "$_herdr_space_pr_key" ]] \
    && (( _herdr_space_pr_checked_at >= 0 && SECONDS - _herdr_space_pr_checked_at < _HERDR_SPACE_PR_TTL )); then
    return 0
  fi
  _herdr_space_pr_key="$key"
  _herdr_space_pr_checked_at=$SECONDS

  _herdr_space_pr_report "$HERDR_WORKSPACE_ID" "$toplevel" "$branch" &!
}

add-zsh-hook precmd _herdr_space_pr_precmd
