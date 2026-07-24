#!/bin/zsh
# AI cross-tool aliases

# カレントウィンドウの絵文字プレフィックス操作に共有実装を使う（未ロード時のみ遅延source）
_ai_ensure_window_name_helper() {
    if ! command -v update_tmux_window_name >/dev/null 2>&1; then
        source "${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/tmux_window_name.sh"
    fi
}

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
            print -r -- "cxh ${prompt_quoted}; zsh"
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

# func_name + クォート済み引数を連結したコマンド文字列を返す（マルチプレクサ非依存）
_ai_review_command() {
    local func_name="$1"
    shift

    local command="${func_name}"
    local arg
    for arg in "$@"; do
        command+=" ${(q)arg}"
    done

    print -r -- "${command}"
}

# tmux new-window用: コマンド実行後もwindowにシェルを残すため "; zsh" を付与
_ai_review_tmux_command() {
    print -r -- "$(_ai_review_command "$@"); zsh"
}

# 現在の実行環境のマルチプレクサ種別を返す: "herdr" | "tmux" | ""
# auto_multiplexer.zsh / plugin.zsh と同じ優先順位（HERDR_ENV最優先、次にTMUX）
_ai_multiplexer_kind() {
    if [[ "${HERDR_ENV:-}" == "1" ]]; then
        print -r -- "herdr"
    elif [[ -n "${TMUX:-}" ]]; then
        print -r -- "tmux"
    else
        print -r -- ""
    fi
}

# 新規Herdrペインの対話シェルが入力を受け付ける状態になるまで待つ。
# herdr tab create / pane split にコマンド起動引数は無く、投入は herdr pane run
# （テキスト+Enter送信のみ・待機機構なし）一択のため、tab create直後にpane runすると
# 新規シェルの起動レースで送信を取りこぼす（gm-pr-review/cx-pr-reviewが起動しない原因）。
# 新規ペインはAIエージェント未検出のためagent_status=unknownのまま推移せず、
# wait agent-status --status idle は使えない。
# 罠が2つある（ライブ検証済み）:
# - zshrc初期化中に pane run で送った入力はバッファされず消えるため、
#   マーカーを1回送って長時間waitしても検出できない。
# - pane wait-output --source recent は入力エコー行を含むため、送信文字列そのままの
#   マーカーはエコーに誤マッチしてシェルready前に成功を返す。
# 対策: マーカーを分割文字列（head""tail）で送り（連結形は実行出力にしか
# 現れない）、短いタイムアウトで送信→waitを繰り返し、シェルready後に
# 実行されたマーカー出力の連結形を検出する。
_herdr_wait_shell_ready() {
    local pane_id="$1"
    local timeout_ms="${2:-24000}"
    local attempt_timeout_ms=800
    local max_attempts=$(( (timeout_ms + attempt_timeout_ms - 1) / attempt_timeout_ms ))

    local marker_head="__herdr_ready_${$}_${RANDOM}"
    local marker_tail="_ok__"
    local marker="${marker_head}${marker_tail}"

    # stderrは捕捉して失敗報告に含める（herdr 0.7.5の `wait output`→`pane wait-output`
    # 改名時、全エラー破棄だとCLI非互換が「タイムアウト」として誤報告された）
    local attempt wait_error=""
    for (( attempt = 1; attempt <= max_attempts; attempt++ )); do
        herdr pane run "${pane_id}" "print -r -- ${marker_head}\"\"${marker_tail}" || return 1
        if wait_error=$(herdr pane wait-output "${pane_id}" --match "${marker}" --source recent --timeout "${attempt_timeout_ms}" 2>&1 >/dev/null); then
            return 0
        fi
    done

    echo "新規ペインのシェル起動待ちがタイムアウトしました (pane_id=${pane_id})" >&2
    [[ -n "${wait_error}" ]] && echo "herdr pane wait-output: ${wait_error}" >&2
    return 1
}

# Herdrで新しいtabを作りコマンドを実行する（tmux new-window相当）
# 引数: workspace_id(空ならカレントworkspace), cwd, label, command
# herdr pane run は既存の対話シェルにコマンドを投入する方式のため、
# tmux版と違い ";  zsh" のようなシェル残存サフィックスは不要
_herdr_run_in_new_tab() {
    local workspace_id="$1"
    local cwd="$2"
    local label="$3"
    local command="$4"

    local -a create_args=(tab create --cwd "${cwd}" --label "${label}" --no-focus)
    [[ -n "${workspace_id}" ]] && create_args+=(--workspace "${workspace_id}")

    local json
    json=$(herdr "${create_args[@]}") || {
        echo "herdr tab createに失敗しました" >&2
        return 1
    }

    local pane_id
    pane_id=$(print -r -- "${json}" | jq -r '.result.root_pane.pane_id')
    if [[ -z "${pane_id}" || "${pane_id}" == "null" ]]; then
        echo "herdr tab createの結果からpane_idを取得できませんでした" >&2
        return 1
    fi

    _herdr_wait_shell_ready "${pane_id}" || return 1

    herdr pane run "${pane_id}" "${command}" || {
        echo "herdr pane runに失敗しました (pane_id=${pane_id})" >&2
        return 1
    }
}

_ai_all_tmux() {
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    local prompt base_name
    prompt="$*"
    base_name=$(_ai_window_base_name) || return 1

    local gemini_name codex_name
    gemini_name="${EMOJI_ID_GEMINI}${base_name}"
    codex_name="${EMOJI_ID_CODEX}${base_name}"

    local gemini_command codex_command
    gemini_command=$(_ai_tmux_command gemini "${prompt}") || return 1
    codex_command=$(_ai_tmux_command codex "${prompt}") || return 1

    tmux new-window -d -n "${gemini_name}" -c "${PWD}" "zsh -ic ${(q)gemini_command}" || return 1
    tmux new-window -d -n "${codex_name}" -c "${PWD}" "zsh -ic ${(q)codex_command}" || return 1

    # カレントウィンドウは Claude 識別絵文字のみ付与（_ai_window_base_name が git 名へ改名済み）
    _ai_ensure_window_name_helper
    update_tmux_window_name "" "${EMOJI_ID_CLAUDE}"
    clhm --permission-mode plan "${prompt}"
}

# tmux非依存・副作用なしでai-all系のベース名(git名、絵文字なし)を計算する
# filter/ai.zsh の _review_window_git_name（純git実装）を流用する
_ai_all_herdr_base_name() {
    if ! command -v _review_window_git_name >/dev/null 2>&1; then
        echo "_review_window_git_name が見つかりません（filter/ai.zsh が未ロード）" >&2
        return 1
    fi
    _review_window_git_name "${PWD}"
}

_ai_herdr_command() {
    local ai="$1"
    local prompt="$2"
    local prompt_quoted="${(q)prompt}"

    # herdr pane run は既存の対話シェルにコマンドを投入する方式のため、
    # tmux版と違い "; zsh" のようなシェル残存サフィックスは不要
    case "${ai}" in
        gemini)
            print -r -- "gmh --approval-mode plan -i ${prompt_quoted}"
            ;;
        codex)
            print -r -- "cxh ${prompt_quoted}"
            ;;
        *)
            return 1
            ;;
    esac
}

# カレントHerdr paneが属するtab_idを解決する（HERDR_TAB_ID優先、無ければ pane get で解決）
_ai_herdr_current_tab_id() {
    if [[ -n "${HERDR_TAB_ID:-}" ]]; then
        print -r -- "${HERDR_TAB_ID}"
        return 0
    fi
    [[ -z "${HERDR_PANE_ID:-}" ]] && return 1
    herdr pane get "${HERDR_PANE_ID}" 2>/dev/null | jq -r '.result.pane.tab_id // empty' 2>/dev/null
}

_ai_all_herdr() {
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    local prompt base_name
    prompt="$*"
    base_name=$(_ai_all_herdr_base_name) || return 1

    local gemini_command codex_command
    gemini_command=$(_ai_herdr_command gemini "${prompt}") || return 1
    codex_command=$(_ai_herdr_command codex "${prompt}") || return 1

    _herdr_run_in_new_tab "" "${PWD}" "${EMOJI_ID_GEMINI}${base_name}" "${gemini_command}" || return 1
    _herdr_run_in_new_tab "" "${PWD}" "${EMOJI_ID_CODEX}${base_name}" "${codex_command}" || return 1

    # カレントtab(Claude)を明示ラベル付けしてから起動。notify-richプラグインは
    # 識別絵文字を発火paneのagentから毎回再導出するため、手動付与と競合しない。
    local tab_id
    tab_id=$(_ai_herdr_current_tab_id)
    [[ -n "${tab_id}" ]] && herdr tab rename "${tab_id}" "${EMOJI_ID_CLAUDE}${base_name}" >/dev/null 2>&1
    clhm --permission-mode plan "${prompt}"
}

ai-all() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: ai-all <prompt>" >&2
        return 1
    fi

    case "$(_ai_multiplexer_kind)" in
        herdr) _ai_all_herdr "$@" ;;
        tmux) _ai_all_tmux "$@" ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac
}

# worktree非依存・tmux非依存でreview系のラベル(AI識別絵文字+🔍+git名)を計算する
# filter/ai.zsh の _review_window_git_name（純git実装）を流用する
# 引数: ai_emoji（省略可。ai-all同様、AI種別を視覚的に区別するための識別絵文字を前置）
_ai_review_herdr_label() {
    local ai_emoji="$1"
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    if ! command -v _review_window_git_name >/dev/null 2>&1; then
        echo "_review_window_git_name が見つかりません（filter/ai.zsh が未ロード）" >&2
        return 1
    fi

    local git_name
    git_name=$(_review_window_git_name "${PWD}")
    echo "${ai_emoji}${EMOJI_STATUS_REVIEW}${git_name}"
}

# label=="review" のHerdr workspaceを探して流用し、無ければ新規作成してworkspace_idを返す
# tmuxのnamed session "review" 相当をHerdrで実現する（filter/ai.zshの都度新規作成方式とは異なり、既存workspaceを優先流用する）
# 引数: cwd（新規作成時の初期tab cwd。既存流用時は無視される）
_herdr_resolve_review_workspace() {
    local cwd="$1"

    local ws_id
    ws_id=$(herdr workspace list 2>/dev/null \
        | jq -r '.result.workspaces[] | select(.label=="review") | .workspace_id' \
        | head -1)
    if [[ -n "${ws_id}" && "${ws_id}" != "null" ]]; then
        print -r -- "${ws_id}"
        return 0
    fi

    local ws_json
    ws_json=$(herdr workspace create --label review --cwd "${cwd}" --no-focus) || {
        echo "herdr workspace createに失敗しました" >&2
        return 1
    }

    ws_id=$(print -r -- "${ws_json}" | jq -r '.result.workspace.workspace_id')
    if [[ -z "${ws_id}" || "${ws_id}" == "null" ]]; then
        echo "review workspaceのworkspace_id取得に失敗しました" >&2
        return 1
    fi
    print -r -- "${ws_id}"
}

_review_tmux() {
    local -a review_args=("$@")

    local review_name gemini_command codex_command
    review_name=$(_review_window_name)
    gemini_command=$(_ai_review_tmux_command gm-pr-review "${review_args[@]}") || return 1
    codex_command=$(_ai_review_tmux_command cx-pr-review "${review_args[@]}") || return 1

    tmux new-window -n "${review_name}" "zsh -ic ${(q)gemini_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)codex_command}"

    # カレントウィンドウは共有実装で🔍を付与（_review_window_name が git 名へ改名済み）
    _ai_ensure_window_name_helper
    update_tmux_window_name "${EMOJI_STATUS_REVIEW}"
    cl-pr-review "${review_args[@]}"
}

_review_herdr() {
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
    claude_command=$(_ai_review_command cl-pr-review "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_command gm-pr-review "${review_args[@]}") || return 1
    codex_command=$(_ai_review_command cx-pr-review "${review_args[@]}") || return 1

    # claudeもgemini/codexと同じくreview workspace内の新規タブで起動する
    # （旧実装はカレントpaneで直接実行しタブ名が「1」のまま残っていた）
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${claude_label}" "${claude_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${gemini_label}" "${gemini_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${codex_label}" "${codex_command}" || return 1

    herdr workspace focus "${ws_id}" >/dev/null 2>&1
}

review() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    case "$(_ai_multiplexer_kind)" in
        herdr) _review_herdr "${review_args[@]}" ;;
        tmux) _review_tmux "${review_args[@]}" ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac
}

_review_subagents_tmux() {
    local -a review_args=("$@")

    local review_name gemini_command codex_command
    review_name=$(_review_window_name)
    gemini_command=$(_ai_review_tmux_command gm-pr-review-subagents "${review_args[@]}") || return 1
    codex_command=$(_ai_review_tmux_command cx-pr-review-subagent "${review_args[@]}") || return 1

    tmux new-window -n "${review_name}" "zsh -ic ${(q)gemini_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)codex_command}"

    # カレントウィンドウは共有実装で🔍を付与（_review_window_name が git 名へ改名済み）
    _ai_ensure_window_name_helper
    update_tmux_window_name "${EMOJI_STATUS_REVIEW}"
    cl-pr-review-subagents "${review_args[@]}"
}

_review_subagents_herdr() {
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
    claude_command=$(_ai_review_command cl-pr-review-subagents "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_command gm-pr-review-subagents "${review_args[@]}") || return 1
    codex_command=$(_ai_review_command cx-pr-review-subagent "${review_args[@]}") || return 1

    # claudeもgemini/codexと同じくreview workspace内の新規タブで起動する
    # （旧実装はカレントpaneで直接実行しタブ名が「1」のまま残っていた）
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${claude_label}" "${claude_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${gemini_label}" "${gemini_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${codex_label}" "${codex_command}" || return 1

    herdr workspace focus "${ws_id}" >/dev/null 2>&1
}

review-subagents() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    case "$(_ai_multiplexer_kind)" in
        herdr) _review_subagents_herdr "${review_args[@]}" ;;
        tmux) _review_subagents_tmux "${review_args[@]}" ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac
}

_review_all_tmux() {
    local -a review_args=("$@")

    local review_name claude_command gemini_command codex_command
    review_name=$(_review_window_name)
    claude_command=$(_ai_review_tmux_command cl-pr-review-subagents "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_tmux_command gm-pr-review-subagents "${review_args[@]}") || return 1
    codex_command=$(_ai_review_tmux_command cx-pr-review-subagent "${review_args[@]}") || return 1

    tmux new-window -n "${review_name}" "zsh -ic ${(q)claude_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)gemini_command}"
    tmux new-window -n "${review_name}" "zsh -ic ${(q)codex_command}"

    # カレントウィンドウは共有実装で🔍を付与（_review_window_name が git 名へ改名済み）
    _ai_ensure_window_name_helper
    update_tmux_window_name "${EMOJI_STATUS_REVIEW}"
    cl-pr-review "${review_args[@]}"
}

_review_all_herdr() {
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
    claude_command=$(_ai_review_command cl-pr-review-subagents "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_command gm-pr-review-subagents "${review_args[@]}") || return 1
    codex_command=$(_ai_review_command cx-pr-review-subagent "${review_args[@]}") || return 1

    # claudeもgemini/codexと同じくreview workspace内の新規タブで起動する
    # （旧実装はカレントpaneで直接実行しタブ名が「1」のまま残っていた）
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${claude_label}" "${claude_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${gemini_label}" "${gemini_command}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${codex_label}" "${codex_command}" || return 1

    herdr workspace focus "${ws_id}" >/dev/null 2>&1
}

review-all() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1

    local review_args=("${pr_number}")
    [[ -n "${review_prompt}" ]] && review_args+=("${review_prompt}")

    case "$(_ai_multiplexer_kind)" in
        herdr) _review_all_herdr "${review_args[@]}" ;;
        tmux) _review_all_tmux "${review_args[@]}" ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac
}
