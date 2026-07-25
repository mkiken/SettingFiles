# source専用の共有関数（zsh/bash両対応）。呼び出し側の流儀に合わせexitは使わずreturnのみ。
#
# 新規Herdrペインの対話シェルが入力を受け付ける状態になるまで待つ。
# herdr tab create / pane split にコマンド起動引数は無く、投入は herdr pane run
# （テキスト+Enter送信のみ・待機機構なし）一択のため、ペイン作成直後にpane runすると
# 新規シェルの起動レースで送信を取りこぼす。
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

    local marker_head="__herdr_ready_$$_${RANDOM}"
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
