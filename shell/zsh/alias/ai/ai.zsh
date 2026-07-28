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

# _herdr_wait_shell_ready はherdr-split-snapshot-pane.sh（bash）と共有するため
# shell/tmux/ の共有ファイルに定義がある
source "${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/herdr_wait_shell_ready.sh"

# Herdrで新しいtabを作りコマンドを実行する（tmux new-window相当）
# 引数: workspace_id(空ならカレントworkspace), cwd, label, command,
#       [tab_id_var(省略可: 作成tabのtab_idを呼び出し元localへ代入する)]
# herdr pane run は既存の対話シェルにコマンドを投入する方式のため、
# tmux版と違い ";  zsh" のようなシェル残存サフィックスは不要
_herdr_run_in_new_tab() {
    local workspace_id="$1"
    local cwd="$2"
    local label="$3"
    local command="$4"
    local tab_id_var="${5:-}"

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

    if [[ -n "${tab_id_var}" ]]; then
        local created_tab_id
        created_tab_id=$(print -r -- "${json}" | jq -r '.result.tab.tab_id // empty')
        # tab_id欠落は致命ではない: 空を代入して続行し、呼び出し元は生存監視なしに退化する
        [[ -z "${created_tab_id}" ]] && echo "herdr tab createの結果からtab_idを取得できませんでした（生存監視なしで続行）" >&2
        _ai_pr_review_assign "${tab_id_var}" "${created_tab_id}" || return 1
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

# 3AIをそれぞれreview workspaceの新規タブで起動する（herdr）
# 引数: claude_tab_var gemini_tab_var codex_tab_var run_dir claude_fn gemini_fn codex_fn review_args...
#   先頭3つは呼び出し元localの変数名で、作成した各サブタブのtab_idを受け取る（生存監視用）
_review_launch_herdr() {
    local claude_tab_var="$1" gemini_tab_var="$2" codex_tab_var="$3"
    local run_dir="$4" claude_fn="$5" gemini_fn="$6" codex_fn="$7"
    shift 7
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
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${claude_label}" "${claude_command}" "${claude_tab_var}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${gemini_label}" "${gemini_command}" "${gemini_tab_var}" || return 1
    _herdr_run_in_new_tab "${ws_id}" "${PWD}" "${codex_label}" "${codex_command}" "${codex_tab_var}" || return 1

    # メインタブ（ウォッチャー→review-merge実行場所）を明示ラベル付けする（ベストエフォート）
    # 注: notify-richはagent無しpaneのfocus時にstatus絵文字を剥がすため🔍は初回focusで消え得る。
    # また手動renameしたラベルはauto_managed=falseになり、以後claudeが動いても本文は自動置換
    # されない＝ "orchestrator:<git名>" はレビュー後も恒久的に残る（許容済みの既知の制限）
    local orchestrator_tab_id orchestrator_git_name
    orchestrator_tab_id=$(_ai_herdr_current_tab_id)
    if [[ -n "${orchestrator_tab_id}" ]]; then
        orchestrator_git_name=$(_review_window_git_name "${PWD}")
        herdr tab rename "${orchestrator_tab_id}" "${EMOJI_STATUS_REVIEW}orchestrator:${orchestrator_git_name}" >/dev/null 2>&1
    fi

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

    local -a wait_cmd_args
    case "$(_ai_multiplexer_kind)" in
        herdr)
            # サブタブのtab_idを受け取り、閉鎖検知(--liveness)付きで待機する
            local claude_tab="" gemini_tab="" codex_tab=""
            _review_launch_herdr claude_tab gemini_tab codex_tab \
                "${run_dir}" "${claude_fn}" "${gemini_fn}" "${codex_fn}" "${review_args[@]}" || return 1
            wait_cmd_args=(--liveness herdr "${run_dir}"
                "claude.md${claude_tab:+=${claude_tab}}"
                "gemini.md${gemini_tab:+=${gemini_tab}}"
                "codex.md${codex_tab:+=${codex_tab}}")
            ;;
        tmux)
            _review_launch_tmux "${run_dir}" "${claude_fn}" "${gemini_fn}" "${codex_fn}" "${review_args[@]}" || return 1
            wait_cmd_args=("${run_dir}" claude.md gemini.md codex.md)
            ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac

    if (( no_merge )); then
        echo "レビューを起動しました（自動マージなし）: ${run_dir}"
        return 0
    fi

    local wait_status=0
    bash "$HOME/.config/ai-pr/bin/ai_review_wait.sh" "${wait_cmd_args[@]}" || wait_status=$?
    _review_handle_wait_status "${wait_status}" "${run_dir}" || return $?
    cl-review-merge "${run_dir}"
}

# 完了待ちの結果からマージ可否を決める。return 0=マージ続行
# exit 3(閉鎖ありで解決)は自動マージせず、揃った分でのマージ可否をユーザーに確認する
_review_handle_wait_status() {
    local wait_status="$1" run_dir="$2"
    case "${wait_status}" in
        0) return 0 ;;
        3)
            local -a arrived=()
            local f
            for f in claude.md gemini.md codex.md; do
                [[ -s "${run_dir}/${f}" ]] && arrived+=("${f}")
            done
            if (( ${#arrived[@]} == 0 )); then
                echo "レビュー結果ファイルが1件もありません（全AIタブが出力前に閉じられました）: ${run_dir}" >&2
                return 1
            fi
            local arrived_names="${(j:, :)${(@)arrived%.md}}"
            if confirm "揃った ${#arrived[@]}/3 件（${arrived_names}）のみでマージしますか？" --default-no --no-cancel-msg; then
                return 0
            fi
            echo "マージを保留しました。揃った分でマージするには review-merge を実行してください: ${run_dir}"
            return 1
            ;;
        *) return "${wait_status}" ;;
    esac
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
