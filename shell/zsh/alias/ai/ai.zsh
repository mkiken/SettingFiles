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
            print -r -- "cl --model opus --permission-mode plan --effort max ${prompt_quoted}; zsh"
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
    cl --model opus --effort max "${prompt}"
}

review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }

    local review_name current_window
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review; zsh'"
    tmux new-window -n "${review_name}" "zsh -ic 'cx-pr-review; zsh'"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review
}

review-subagents() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }

    local review_name current_window
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review-subagents; zsh'"
    tmux new-window -n "${review_name}" "zsh -ic 'cx-pr-review-subagent; zsh'"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review-subagents
}

review-all() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }

    local review_name current_window
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'cl-pr-review-subagents; zsh'"
    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review-subagents; zsh'"
    tmux new-window -n "${review_name}" "zsh -ic 'cx-pr-review-subagent; zsh'"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review
}
