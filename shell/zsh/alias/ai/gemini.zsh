#!/bin/zsh

gm-update() {
    homebrew_npm install -g @google/gemini-cli@latest
}

gm() {
    no_notify homebrew_run gemini "$@"
}

gmr() { gm "/resume" "$@" }

gmpr() { gmp "/resume" "$@" }

# `f` selects Flash.
gmf() {
    gm --model flash "$@"
}

# `p` selects Pro.
gmp() {
    gm --model pro "$@"
}

gmh() {
    gmp "$@"
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

gmhp() {
    gmh --approval-mode plan "$@"
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
    gmh --approval-mode yolo -i "/pr-review $pr_number${review_prompt:+ $review_prompt} $(_ai_gemini_failsafe_note "$pr_number")"
}

gm-pr-review-subagent() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    gmh --approval-mode yolo -i "/pr-review-subagents $pr_number${review_prompt:+ $review_prompt} $(_ai_gemini_failsafe_note "$pr_number")"
}
alias gm-pr-review-subagents='gm-pr-review-subagent'

gm-pr-body() {
    gmh -i "/pr-body $*"
}

alias gm-pr-comment-review='noglob _gm-pr-comment-review'
alias gm-pcr='noglob _gm-pr-comment-review'
_gm-pr-comment-review() {
    gmh --approval-mode yolo -i "/pr-comment-review $*"
}

alias gm-pr-comment-implement='noglob _gm-pr-comment-implement'
alias gm-pci='noglob _gm-pr-comment-implement'
_gm-pr-comment-implement() {
    gmh -i "/pr-comment-implement $*"
}

gm-web-summary() {
    gmh --allowed-tools "WebFetchTool" -i "/web-summary $*"
}
