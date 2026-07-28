#!/bin/bash
# ランディレクトリに期待する結果ファイルが全て(非空で)揃うまでポーリングして待つ。
# 使い方: ai_review_wait.sh [--liveness herdr] <run_dir> <file>[=<handle>]...
#   handle はマルチプレクサ上のタブ識別子（herdr: tab_id）。--liveness 指定時のみ使われ、
#   タブ消滅かつファイル未生成のAIを「閉鎖」として完了待ちから除外する。
# 環境変数: AI_REVIEW_WAIT_INTERVAL(default 5) / AI_REVIEW_WAIT_TIMEOUT(default 7200)
# 終了コード: 0=揃った / 1=引数不正 / 2=タイムアウト / 3=閉鎖ありで解決(ファイルは不揃いの可能性)
# 進捗表示はstderrの複数行ダッシュボード(ブロック上書き)。中断はCtrl-C。
# 既知の制限: カーソル戻し(\033[NA)は論理行ベースのため、端末幅が狭く行が折り返すと表示が崩れる。

set -u

# 生存確認(herdr): tab getが成功しtab_idが一致すればalive
_ai_review_tab_alive_herdr() {
    local tab_id="$1" got
    got=$(herdr tab get "${tab_id}" 2>/dev/null | jq -r '.result.tab.tab_id // empty' 2>/dev/null)
    [[ "${got}" == "${tab_id}" ]]
}

# CLI/デーモン到達性プローブ。tab get失敗時のみ事後実行し、失敗中はその失敗を
# 「確定失敗」として数えない(fail-open: herdr障害時はタイムアウト挙動に退化)
_ai_review_liveness_probe_herdr() {
    herdr workspace list >/dev/null 2>&1
}

# 完了ファイルの表示用サイズ(1024未満はB、それ以上はKB)
_ai_review_file_size() {
    wc -c < "$1" 2>/dev/null | awk '{ if ($1 < 1024) printf "%dB", $1; else printf "%.1fKB", $1/1024 }'
}

main() {
    local usage="Usage: ai_review_wait.sh [--liveness herdr] <run_dir> <file>[=<handle>]..."
    local liveness=""
    if [[ "${1:-}" == "--liveness" ]]; then
        liveness="${2:-}"
        shift 2 || true
        if [[ "${liveness}" != "herdr" ]]; then
            echo "${usage}" >&2
            return 1
        fi
    fi

    local run_dir="${1:-}"
    if [[ -z "$run_dir" || $# -lt 2 ]]; then
        echo "${usage}" >&2
        return 1
    fi
    shift

    local interval="${AI_REVIEW_WAIT_INTERVAL:-5}"
    local timeout="${AI_REVIEW_WAIT_TIMEOUT:-7200}"
    local start_epoch elapsed
    start_epoch=$(date +%s)

    local -a names=() handles=() closed=() miss=()
    local spec
    for spec in "$@"; do
        names+=("${spec%%=*}")
        if [[ "${spec}" == *=* ]]; then
            handles+=("${spec#*=}")
        else
            handles+=("")
        fi
        closed+=(0)
        miss+=(0)
    done

    local drawn_lines=0
    while :; do
        local pending=0 any_closed=0 probe_state="" i
        local -a lines=()
        for i in "${!names[@]}"; do
            local f="${names[i]}"
            local display="${f%.md}"
            # ファイル判定が最優先(=閉鎖後にファイルが届いたケースも✓として扱う)
            if [[ -s "${run_dir}/${f}" ]]; then
                lines+=("  ${display}: 完了✓ (${f} $(_ai_review_file_size "${run_dir}/${f}"))")
                continue
            fi
            if (( closed[i] == 0 )) && [[ -n "${liveness}" && -n "${handles[i]}" ]]; then
                if "_ai_review_tab_alive_${liveness}" "${handles[i]}"; then
                    miss[i]=0
                else
                    # 事後プローブ(イテレーション内キャッシュ): プローブ成功が確認できた失敗だけ数える
                    if [[ -z "${probe_state}" ]]; then
                        "_ai_review_liveness_probe_${liveness}" && probe_state=ok || probe_state=down
                    fi
                    if [[ "${probe_state}" == ok ]]; then
                        miss[i]=$(( miss[i] + 1 ))
                        # 2イテレーション連続の確定失敗で✗確定(デバウンス、以後sticky)
                        (( miss[i] >= 2 )) && closed[i]=1
                    fi
                fi
            fi
            if (( closed[i] )); then
                lines+=("  ${display}: 閉鎖✗（タブ消滅・出力なし）")
                any_closed=1
            elif [[ -n "${liveness}" && -n "${handles[i]}" ]]; then
                lines+=("  ${display}: 実行中（タブ生存・出力待ち）")
                pending=1
            else
                lines+=("  ${display}: 実行中（出力待ち）")
                pending=1
            fi
        done

        elapsed=$(( $(date +%s) - start_epoch ))
        # 2回目以降は前回描画ブロックへカーソルを戻して上書きする
        (( drawn_lines > 0 )) && printf '\033[%dA' "${drawn_lines}" >&2
        printf '\r\033[Kレビュー完了待ち (%ds)\n' "${elapsed}" >&2
        local line
        for line in "${lines[@]}"; do
            printf '\r\033[K%s\n' "${line}" >&2
        done
        drawn_lines=$(( ${#lines[@]} + 1 ))

        if (( pending == 0 )); then
            if (( any_closed )); then
                # 最終再チェック: クローズ確定とファイル出現が同一イテレーションで
                # 交錯した場合の保険。全部揃っていれば正常完了として扱う
                local all_present=1
                for i in "${!names[@]}"; do
                    [[ -s "${run_dir}/${names[i]}" ]] || all_present=0
                done
                (( all_present )) && return 0
                printf '一部のAIタブが結果ファイル出力前に閉じられました。\n' >&2
                return 3
            fi
            return 0
        fi
        if (( elapsed >= timeout )); then
            # ダッシュボード最終状態は上に残る(「タブ生存のまま出力なし」等の診断に使う)
            printf 'タイムアウト(%ds)。揃った分だけでマージするには review-merge を手動実行してください。\n' "${timeout}" >&2
            return 2
        fi
        sleep "$interval"
    done
}

main "$@"
