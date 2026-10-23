#!/bin/zsh

# Gemini CLI のバージョン固定の唯一の定義場所（mac/initialization・mac/updates もここを経由する）。
# 0.61.0 以降で shell 出力由来のトークンを「信頼できないフラグ」と誤検知し、確認ダイアログが
# 会話中に何度も出る（上流 issue #29579 / #29676）。0.64.0 でも改善が不十分だったため 0.60.0 に固定。
# 解除: 上流で誤検知の解消を確認できたら latest に戻す。
gm-update() {
    local pinned_version="0.60.0"
    homebrew_npm install -g "@google/gemini-cli@${pinned_version}"
}

gm() {
    no_notify homebrew_run gemini "$@"
}

_gm_resume_with_picker() {
    local runner="$1"
    shift
    if [[ $# -eq 0 ]]; then
        if ! command -v fzf >/dev/null 2>&1; then
            echo "fzf が見つかりません。最新セッションを再開します。" >&2
            "$runner" --resume
            return
        fi
        local session_line session_index rest
        session_line=$("$runner" --list-sessions 2>/dev/null | grep -E '^[[:space:]]*[0-9]+\.' | fzf --tac --no-sort --reverse --prompt="Select Gemini session: ")
        [[ -z "$session_line" ]] && return 0
        read -r session_index rest <<< "$session_line"
        session_index="${session_index%.}"
        if [[ "$session_index" =~ ^[0-9]+$ ]]; then
            "$runner" --resume "$session_index"
        fi
    else
        "$runner" --resume "$@"
    fi
}

gmr() { _gm_resume_with_picker gm "$@" }

gmpr() { _gm_resume_with_picker gmp "$@" }

# `f` selects Flash.
gmf() {
    gm --model flash "$@"
}

# `p` selects Pro.
gmp() {
    gm --model pro "$@"
}

gmmx() {
    gmf "$@"
}

gml() {
    gmf "$@"
}

gmfp() {
    gmf --approval-mode plan "$@"
}

gmpp() {
    gmp --approval-mode plan "$@"
}

gmmxp() {
    gmmx --approval-mode plan "$@"
}

gmlp() {
    gml --approval-mode plan "$@"
}

# gemini-cliの既知のレース（カスタムコマンドが非同期ロード中に初期プロンプトが処理されうる）で
# スラッシュコマンド展開が失敗すると、raw文字列がそのままモデルへ渡る。先頭を正規のスラッシュ
# コマンド形式に保ちつつ、展開失敗時も文章として意味が通るようPR番号込みの自然文を続ける。
# 括弧内はGEMINI.mdのSlash Command Failsafeが参照するフェイルセーフ用マーカーで、展開成功時は
# 各pr-review系tomlのInputs節が追加指示から読み替えて捨てる
_ai_gemini_failsafe_note() {
    local pr_number="$1"
    print -r -- "(このメッセージがスラッシュコマンドとして展開されている場合、この括弧以降は無視して通常どおりレビューしてください。展開されていない場合は PR #${pr_number} のレビューです — GEMINI.md の Slash Command Failsafe に従ってください)"
}

gm-pr-review() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    gmmx --approval-mode yolo -i "/pr-review $pr_number${review_prompt:+ $review_prompt} $(_ai_gemini_failsafe_note "$pr_number")"
}

gm-pr-review-subagent() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    gmmx --approval-mode yolo -i "/pr-review-subagents $pr_number${review_prompt:+ $review_prompt} $(_ai_gemini_failsafe_note "$pr_number")"
}
alias gm-pr-review-subagents='gm-pr-review-subagent'

gm-pr-body() {
    gmmx -i "/pr-body $*"
}

alias gm-pr-comment-review='noglob _gm-pr-comment-review'
alias gm-pcr='noglob _gm-pr-comment-review'
_gm-pr-comment-review() {
    gmmx --approval-mode yolo -i "/pr-comment-review $*"
}

alias gm-pr-comment-implement='noglob _ai_pci_route _gm-pr-comment-implement'
alias gm-pci='noglob _ai_pci_route _gm-pr-comment-implement'
_gm-pr-comment-implement() {
    gmmx -i "/pr-comment-implement $*"
}

gm-web-summary() {
    gmmx --allowed-tools "WebFetchTool" -i "/web-summary $*"
}
