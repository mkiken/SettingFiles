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
            print -r -- "clh --permission-mode plan ${prompt_quoted}; zsh"
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
#       [tab_id_var(省略可: 作成tabのtab_idを呼び出し元localへ代入する)],
#       [focus_on_create(省略可: 1なら作成直後にフォーカス)]
# herdr pane run は既存の対話シェルにコマンドを投入する方式のため、
# tmux版と違い ";  zsh" のようなシェル残存サフィックスは不要
_herdr_run_in_new_tab() {
    local workspace_id="$1"
    local cwd="$2"
    local label="$3"
    local command="$4"
    local tab_id_var="${5:-}"
    local focus_on_create="${6:-0}"

    local -a create_args=(tab create --cwd "${cwd}" --label "${label}")
    if [[ "${focus_on_create}" == "1" ]]; then
        create_args+=(--focus)
    else
        create_args+=(--no-focus)
    fi
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
    clh --permission-mode plan "${prompt}"
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
    clh --permission-mode plan "${prompt}"
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
# 引数: ai_emoji（省略可。ai-all同様、AI種別を視覚的に区別するための識別絵文字を前置） cwd（レビュー対象ディレクトリ）
_ai_review_herdr_label() {
    local ai_emoji="$1"
    local cwd="$2"
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    if ! command -v _review_window_git_name >/dev/null 2>&1; then
        echo "_review_window_git_name が見つかりません（filter/ai.zsh が未ロード）" >&2
        return 1
    fi

    local git_name
    git_name=$(_review_window_git_name "${cwd}")
    echo "${ai_emoji}${EMOJI_STATUS_REVIEW}${git_name}"
}

# レビュー実行ごとに専用のHerdr workspace（label: review-<ディレクトリ名>）を新規作成し、
# 作成応答のJSONをそのまま出力する（workspace_id/初期タブ/root paneを呼び出し元が使う）
# 引数: cwd（初期tabのcwd。ラベルのディレクトリ名にも使う）
_herdr_create_review_workspace() {
    local cwd="$1"

    local ws_json
    ws_json=$(herdr workspace create --label "review-${cwd:t}" --cwd "${cwd}" --no-focus) || {
        echo "herdr workspace createに失敗しました" >&2
        return 1
    }
    print -r -- "${ws_json}"
}

# 3AIをレビュー実行ごとの専用workspace（review-<ディレクトリ名>）の新規タブで起動する（herdr）
# 引数: create_watcher(1なら完了待ち〜マージをworkspaceの初期タブ=orchestratorタブで実行) run_dir claude_fn gemini_fn codex_fn review_args...
# 呼び出し元タブは拘束しない: 完了待ち〜マージはworkspace作成時にできる初期タブを
# orchestratorタブ（_review_watch実行）として使い、そちらへ委譲する
_review_launch_herdr() {
    local create_watcher="$1" run_dir="$2" claude_fn="$3" gemini_fn="$4" codex_fn="$5"
    shift 5
    local -a review_args=("$@")

    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"

    # レビュー対象ディレクトリ: AI_REVIEW_CWDが未設定なら$PWD（従来どおり）
    # worktreeピッカー経由のfreviewはコマンド前置でこれを渡し、workspace/タブ/ラベルを
    # 選択worktree基準にする（exportしないため並列実行でも他プロセスへ漏れない）
    local review_cwd="${AI_REVIEW_CWD:-${PWD}}"

    local claude_label gemini_label codex_label
    local claude_command gemini_command codex_command
    # ラベル計算（git名依存）を先に行い、失敗時は無駄なworkspace作成を避ける
    claude_label=$(_ai_review_herdr_label "${EMOJI_ID_CLAUDE}" "${review_cwd}") || return 1
    gemini_label=$(_ai_review_herdr_label "${EMOJI_ID_GEMINI}" "${review_cwd}") || return 1
    codex_label=$(_ai_review_herdr_label "${EMOJI_ID_CODEX}" "${review_cwd}") || return 1
    claude_command=$(_ai_review_env_command "${run_dir}/claude.md" "${claude_fn}" "${review_args[@]}") || return 1
    gemini_command=$(_ai_review_env_command "${run_dir}/gemini.md" "${gemini_fn}" "${review_args[@]}") || return 1
    codex_command=$(_ai_review_env_command "${run_dir}/codex.md" "${codex_fn}" "${review_args[@]}") || return 1

    local ws_json ws_id orch_tab_id orch_pane_id
    ws_json=$(_herdr_create_review_workspace "${review_cwd}") || return 1
    ws_id=$(print -r -- "${ws_json}" | jq -r '.result.workspace.workspace_id // empty')
    if [[ -z "${ws_id}" ]]; then
        echo "review workspaceのworkspace_id取得に失敗しました" >&2
        return 1
    fi
    orch_tab_id=$(print -r -- "${ws_json}" | jq -r '.result.tab.tab_id // empty')
    orch_pane_id=$(print -r -- "${ws_json}" | jq -r '.result.root_pane.pane_id // empty')

    # Claudeも新規タブで起動し、tab_idを閉鎖検知(--liveness)用に控える
    local claude_tab="" gemini_tab="" codex_tab=""
    _herdr_run_in_new_tab "${ws_id}" "${review_cwd}" "${claude_label}" "${claude_command}" claude_tab || return 1
    _herdr_run_in_new_tab "${ws_id}" "${review_cwd}" "${gemini_label}" "${gemini_command}" gemini_tab || return 1
    _herdr_run_in_new_tab "${ws_id}" "${review_cwd}" "${codex_label}" "${codex_command}" codex_tab || return 1

    if [[ "${create_watcher}" == "1" ]]; then
        if [[ -z "${orch_pane_id}" ]]; then
            echo "review workspaceのroot pane取得に失敗しました" >&2
            return 1
        fi
        # 初期タブをorchestratorタブとして使う: ラベル付けして完了待ち〜マージを投入する
        # 注: renameした手動ラベルはauto_managed=falseのため、マージでclaudeが動いても
        # 本文は自動置換されず "orchestrator:<git名>" が残り続ける（専用タブなので意図どおり）
        local orchestrator_git_name watch_command
        orchestrator_git_name=$(_review_window_git_name "${review_cwd}")
        [[ -n "${orch_tab_id}" ]] && herdr tab rename "${orch_tab_id}" \
            "${EMOJI_STATUS_REVIEW}orchestrator:${orchestrator_git_name}" >/dev/null 2>&1
        watch_command="_review_watch ${(q)run_dir}"
        watch_command+=" ${(q):-claude.md${claude_tab:+=${claude_tab}}}"
        watch_command+=" ${(q):-gemini.md${gemini_tab:+=${gemini_tab}}}"
        watch_command+=" ${(q):-codex.md${codex_tab:+=${codex_tab}}}"
        _herdr_wait_shell_ready "${orch_pane_id}" || return 1
        herdr pane run "${orch_pane_id}" "${watch_command}" || {
            echo "herdr pane runに失敗しました (pane_id=${orch_pane_id})" >&2
            return 1
        }
    fi

    herdr workspace focus "${ws_id}" >/dev/null 2>&1
    # 完了待ちダッシュボードがすぐ見えるようorchestratorタブへフォーカスする（ベストエフォート）
    [[ "${create_watcher}" == "1" && -n "${orch_tab_id}" ]] && herdr tab focus "${orch_tab_id}" >/dev/null 2>&1
    return 0
}

# orchestratorタブ内で実行される: 完了待ち→(出揃い時)3AIタブを閉じる→マージ可否判断→cl-review-merge
# 引数: run_dir <file>[=<tab_id>]...
_review_watch() {
    local run_dir="$1"
    shift

    local -a specs=("$@")
    local wait_status=0
    bash "$HOME/.config/ai-pr/bin/ai_review_wait.sh" --liveness herdr "${run_dir}" "${specs[@]}" || wait_status=$?

    # 3AIタブが必要なのは成果物ファイルの生成までなので、出揃った時点（マージ前）で閉じる。
    # マージはファイルが残っていれば review-merge で再実行できるため、その成否をgateにしない。
    # 不揃い(exit 3)のときは未出力のAIタブを手で確認できるよう残す
    if (( wait_status == 0 )); then
        local -a tab_ids=()
        local spec tab_id
        for spec in "${specs[@]}"; do
            tab_id="${spec#*=}"
            [[ "${tab_id}" != "${spec}" && -n "${tab_id}" ]] && tab_ids+=("${tab_id}")
        done
        _review_close_ai_tabs "${tab_ids[@]}"
    fi

    _review_handle_wait_status "${wait_status}" "${run_dir}" || return $?
    cl-review-merge "${run_dir}"
}

# レビュー用に開いた3AIタブ（herdr）を確認なしで閉じる。tmux未対応（no-op）
# 呼び出し元が3AIの成果物ファイル出揃いを確認済みのため、マージは review-merge <run_dir> で
# 後から再実行できる。よって会話ログ以外は失われない前提で即クローズする
# 引数: tab_id...（liveness検知用に控えていたもの。空要素は無視する）
_review_close_ai_tabs() {
    if [[ "$(_ai_multiplexer_kind)" != "herdr" ]]; then
        return 0
    fi

    local self_tab_id
    self_tab_id=$(_ai_herdr_current_tab_id)

    local -a candidates=()
    local tab_id
    for tab_id in "$@"; do
        [[ -z "${tab_id}" ]] && continue
        # orchestratorタブ（自タブ）は誤爆防止のため候補から除外する
        [[ -n "${self_tab_id}" && "${tab_id}" == "${self_tab_id}" ]] && continue
        herdr tab get "${tab_id}" >/dev/null 2>&1 && candidates+=("${tab_id}")
    done

    if (( ${#candidates[@]} == 0 )); then
        echo "レビュー用のAIタブは既にすべて閉じられています。"
        return 0
    fi

    # 無言でタブが消えると原因が追えないため、クローズ前に理由を1行残す
    echo "レビュー用のAIタブ（${#candidates[@]}件）を閉じます。（会話ログは失われますが、claude.md/gemini.md/codex.md は保存済みでマージは後から再実行できます）"

    for tab_id in "${candidates[@]}"; do
        herdr tab close "${tab_id}" >/dev/null 2>&1 || echo "herdr tab closeに失敗しました (tab_id=${tab_id})" >&2
    done
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
# herdrではレビューごとに専用workspace(review-<ディレクトリ名>)を作り、完了待ち以降を
# その初期タブ=orchestratorタブ(_review_watch)へ委譲して即return、
# tmuxでは従来どおりカレントウィンドウで完了待ちする
# 環境変数 AI_REVIEW_CWD が設定されていれば、herdr経路のworkspace/タブ/ラベルは
# $PWD ではなくそのパスを基準にする（worktreeピッカー経由のfreviewが使う）
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
        herdr)
            # 完了待ち〜マージはreview workspaceのorchestratorタブへ委譲し、呼び出し元タブは即解放する
            local create_watcher=1
            (( no_merge )) && create_watcher=0
            _review_launch_herdr "${create_watcher}" \
                "${run_dir}" "${claude_fn}" "${gemini_fn}" "${codex_fn}" "${review_args[@]}" || return 1
            if (( no_merge )); then
                echo "レビューを起動しました（自動マージなし）: ${run_dir}"
            else
                echo "レビューを起動しました。完了待ち〜マージは review-${${AI_REVIEW_CWD:-${PWD}}:t} スペースの🔍orchestratorタブで実行します: ${run_dir}"
            fi
            return 0
            ;;
        tmux)
            _review_launch_tmux "${run_dir}" "${claude_fn}" "${gemini_fn}" "${codex_fn}" "${review_args[@]}" || return 1
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
    bash "$HOME/.config/ai-pr/bin/ai_review_wait.sh" "${run_dir}" claude.md gemini.md codex.md || wait_status=$?
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

# 引数(PR参照 or 現ブランチ)から最新ランディレクトリを解決する（review-merge/review-report共用）
# 呼び出し元localへ run_dir_var 経由で代入する
_ai_pr_review_resolve_latest_run_dir() {
    local run_dir_var="$1"
    shift

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
    _ai_pr_review_assign "${run_dir_var}" "${run_dir}"
}

# 手動マージ（救済用）: 最新ランディレクトリを解決して review-merge スキルを起動する
review-merge() {
    local run_dir
    _ai_pr_review_resolve_latest_run_dir run_dir "$@" || return 1
    cl-review-merge "${run_dir}"
}

# 後日レビュー結果を見返す/判断を再開する: 最新ランディレクトリのreport.htmlを
# サーバー経由で開く（同じrun_dirへの既存サーバーがあれば再利用し、Finderダイアログに落ちる
# file://直開きを避ける）
review-report() {
    local run_dir
    _ai_pr_review_resolve_latest_run_dir run_dir "$@" || return 1

    if [[ ! -f "${run_dir}/report.html" ]]; then
        echo "report.htmlが見つかりません（review-merge未実行）: ${run_dir}" >&2
        return 1
    fi

    nohup python3 "$HOME/.config/ai-pr/bin/serve_review_report.py" --open "${run_dir}" >/dev/null 2>&1 &
    echo "レビュー結果を開いています: ${run_dir}"
}
