# source専用の共有関数（zsh/bash両対応）。呼び出し側の流儀に合わせexitは使わずreturnのみ。
#
# 新規Herdrペインの対話シェルが入力を受け付ける状態になるまで待つ。
# herdr tab create / pane split にコマンド起動引数は無く、投入は herdr pane run
# （テキスト+Enter送信のみ・待機機構なし）一択のため、ペイン作成直後にpane runすると
# 新規シェルの起動レースで送信を取りこぼす。
# 新規ペインはAIエージェント未検出のためagent_status=unknownのまま推移せず、
# wait agent-status --status idle は使えない。
# 罠が3つある（すべてライブ検証済み）:
# - zshrc初期化中に pane run で送った入力はバッファされず消えるため、
#   マーカーを1回送って長時間waitしても検出できない。
# - pane wait-output --source recent は入力エコー行を含むため、送信文字列そのままの
#   マーカーはエコーに誤マッチしてシェルready前に成功を返す。
# - pane wait-output --source recent は累積スナップショットを検索するため、
#   全attemptで同一マーカーを再送すると、一度マーカーの実行出力が載った後は
#   ペインの状態と無関係に即マッチする。zshrc初期化中にreadyと誤判定して本命
#   コマンドを送ると、行として確定していない過去の送信が行バッファに残っている
#   ところへ連結され、本命が `print -r -- <本命>` の引数として echo されるだけで
#   実行されない（freviewのcodexタブでレビューが始まらない不具合の主原因）。
# 対策: マーカーを分割文字列（head""tail）で送り（連結形は実行出力にしか
# 現れない）、attempt毎にユニークなマーカーを使い、短いタイムアウトで送信→waitを
# 繰り返して、実行されたマーカー出力の連結形を検出する。ready後に ctrl+u で
# 行バッファを空にし、本命コマンドが空の行に着地することを保証する。
#
# 採用しなかった対策（いずれもライブ実測で否定済み。再検討を避けるため記録する）:
# - pane wait-output --lines N での検索範囲の境界付け: --lines は末尾N行ではなく
#   固定高グリッドの上端からN行を切り出す。可視内容4行のペインで --lines 1..50 は
#   全てNOMATCH、100以上でMATCH。内容は下端にあるためNを小さくすると現在のattemptの
#   出力ごと切り落ちる。--lines 3 を入れた設計は正常ペインで attempts=12 ok=0 となり、
#   間欠的不具合が恒常的な起動失敗に悪化した。
# - pane process-info による非侵襲ポーリング: 新規ペインでは
#   foreground_process_group_id == shell_pid が1サンプル目から常に成立する
#   （zshrc実行中のシェルもフォアグラウンドはzsh自身）。待ちたい区間で常にreadyと答える。
# - 各attempt先頭での ctrl+u パージ: ZLE起動前の ctrl+u は無力。8回連打した直後に
#   本命を送っても TTY にエコーされるだけで実行されず消滅した。有効なのはZLE起動後
#   （=ready判定後）のみ。
_herdr_wait_shell_ready() {
    local pane_id="$1"
    local timeout_ms="${2:-24000}"
    local attempt_timeout_ms=800
    local max_attempts=$(( (timeout_ms + attempt_timeout_ms - 1) / attempt_timeout_ms ))

    # マーカーはattempt毎にユニークにする（累積スナップショットへのstaleマッチ防止）
    local marker_prefix="__herdr_ready_$$_${RANDOM}"
    local marker_tail="_ok__"

    # stderrは捕捉して失敗報告に含める（herdr 0.7.5の `wait output`→`pane wait-output`
    # 改名時、全エラー破棄だとCLI非互換が「タイムアウト」として誤報告された）
    local attempt marker_head marker wait_error=""
    for (( attempt = 1; attempt <= max_attempts; attempt++ )); do
        marker_head="${marker_prefix}_${attempt}"
        marker="${marker_head}${marker_tail}"
        herdr pane run "${pane_id}" "print -r -- ${marker_head}\"\"${marker_tail}" || return 1
        if wait_error=$(herdr pane wait-output "${pane_id}" --match "${marker}" --source recent --timeout "${attempt_timeout_ms}" 2>&1 >/dev/null); then
            # 本命コマンドが空の行に着地するよう行バッファをクリアする
            herdr pane send-keys "${pane_id}" ctrl+u || return 1
            return 0
        fi
    done

    echo "新規ペインのシェル起動待ちがタイムアウトしました (pane_id=${pane_id})" >&2
    [[ -n "${wait_error}" ]] && echo "herdr pane wait-output: ${wait_error}" >&2
    return 1
}
