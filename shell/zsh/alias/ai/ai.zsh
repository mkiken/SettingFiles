#!/bin/zsh
# AI cross-tool aliases

# rename-window-git.sh を呼んで git ベースのウィンドウ名を計算し、🔍プレフィックス付きで返す
_review_window_name() {
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"
    "${set_dir}/shell/tmux/rename-window-git.sh"
    local git_name
    git_name=$(tmux display-message -p '#W')
    # 絵文字プレフィックスを除去してから 🔍 を付与（アイコンスタック防止）
    git_name=$(python3 "${set_dir}/shell/tmux/tmux_emoji.py" "${git_name}")
    echo "${EMOJI_STATUS_REVIEW}${git_name}"
}

_ai_window_base_name() {
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    "${set_dir}/shell/tmux/rename-window-git.sh"
    local git_name
    git_name=$(tmux display-message -p '#W')
    python3 "${set_dir}/shell/tmux/tmux_emoji.py" "${git_name}"
}

_ai_tmux_command() {
    local ai="$1"
    local prompt="$2"
    local prompt_quoted="${(q)prompt}"

    case "${ai}" in
        claude)
            print -r -- "clhm --permission-mode plan ${prompt_quoted}; zsh"
            ;;
        gemini)
            print -r -- "gmh --approval-mode plan -i ${prompt_quoted}; zsh"
            ;;
        codex)
            print -r -- "cx -c 'model_reasoning_effort=\"xhigh\"' --sandbox read-only ${prompt_quoted}; zsh"
            ;;
        *)
            return 1
            ;;
    esac
}

_ai_pr_review_arg_is_pr_ref() {
    [[ "$1" =~ '^(#?[0-9]+|https?://[^[:space:]]+/pull/[0-9]+([/?#].*)?)$' ]]
}

_ai_pr_review_assign() {
    local name="$1"
    local value="$2"

    [[ "${name}" =~ '^[A-Za-z_][A-Za-z0-9_]*$' ]] || return 1
    eval "${name}=${(q)value}"
}

_ai_pr_review_resolve_args() {
    local pr_var="$1"
    local prompt_var="$2"
    shift 2

    local resolved_pr_number resolved_review_prompt
    if [[ $# -gt 0 ]] && _ai_pr_review_arg_is_pr_ref "$1"; then
        resolved_pr_number="${1#\#}"
        shift
    else
        resolved_pr_number=$(gh pr view --json number --jq .number) || {
            echo "現在のブランチに対応するPRが見つかりません。" >&2
            return 1
        }
    fi

    resolved_review_prompt="$*"
    _ai_pr_review_assign "${pr_var}" "${resolved_pr_number}" || return 1
    _ai_pr_review_assign "${prompt_var}" "${resolved_review_prompt}" || return 1
}

_ai_review_tmux_command() {
    local func_name="$1"
    shift

    local command="${func_name}"
    local arg
    for arg in "$@"; do
        command+=" ${(q)arg}"
    done

    print -r -- "${command}; zsh"
}

ai-all() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: ai-all <prompt>" >&2
        return 1
    fi

    if [[ -z "${TMUX:-}" ]]; then
        echo "tmux内で実行してください" >&2
        return 1
    fi

    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    local prompt base_name current_window
    prompt="$*"
    current_window=$(tmux display-message -p '#{window_id}') || return 1
    base_name=$(_ai_window_base_name) || return 1

    local claude_name gemini_name codex_name
    claude_name="${EMOJI_ID_CLAUDE}${base_name}"
    gemini_name="${EMOJI_ID_GEMINI}${base_name}"
    codex_name="${EMOJI_ID_CODEX}${base_name}"

    local gemini_command codex_command
    gemini_command=$(_ai_tmux_command gemini "${prompt}") || return 1
    codex_command=$(_ai_tmux_command codex "${prompt}") || return 1

    tmux new-window -d -n "${gemini_name}" -c "${PWD}" "zsh -ic ${(q)gemini_command}" || return 1
    tmux new-window -d -n "${codex_name}" -c "${PWD}" "zsh -ic ${(q)codex_command}" || return 1

    tmux rename-window -t "${current_window}" "${claude_name}" || return 1
    clhm --permission-mode plan "${prompt}"
}

review() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    local review_name current_window gemini_command codex_command
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)
    gemini_command=$(_ai_review_tmux_command gm-pr-review "${review_args[@]}") || return 1
    codex_command=$(_ai_review_tmux_command cx-pr-review "${review_args[@]}") || return 1

    tmux new-window -n "${review_name}" "zsh -ic ${(q)gemini_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)codex_command}"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review "${review_args[@]}"
}

review-subagents() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    local review_name current_window gemini_command codex_command
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)
    gemini_command=$(_ai_review_tmux_command gm-pr-review-subagents "${review_args[@]}") || return 1
    codex_command=$(_ai_review_tmux_command cx-pr-review-subagent "${review_args[@]}") || return 1

    tmux new-window -n "${review_name}" "zsh -ic ${(q)gemini_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)codex_command}"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review-subagents "${review_args[@]}"
}

review-all() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    local review_name current_window claude_command gemini_command codex_command
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)
    claude_command=$(_ai_review_tmux_command cl-pr-review-subagents "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_tmux_command gm-pr-review-subagents "${review_args[@]}") || return 1
    codex_command=$(_ai_review_tmux_command cx-pr-review-subagent "${review_args[@]}") || return 1

    tmux new-window -n "${review_name}" "zsh -ic ${(q)claude_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)gemini_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)codex_command}"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review "${review_args[@]}"
}
