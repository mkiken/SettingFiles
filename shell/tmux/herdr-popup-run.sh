#!/bin/bash
# Herdr popup の共通ラッパー。popup はコマンド終了と同時にタブが閉じるため、
# エラー終了時に何が起きたか読めないまま消える。全 popup をこれで包み、
# エラー終了時だけキー入力を待って原因を読み切れるようにする。
#
# 使い方: herdr-popup-run.sh <command> [args...]
#   例) herdr-popup-run.sh zsh -ilc 'freview'
# eval は使わない。引数配列をそのまま起動する。
#
# 個別 pause との併存（フラグファイル方式）:
#   HERDR_POPUP_PAUSE_MARK に一時ファイルパスを入れて子へ渡す。
#   子側で個別 pause を実行したらそのファイルへ書き込む。
#   ラッパーはマークが非空なら自分は pause しない = 個別 pause 優先、
#   無ければラッパーが拾う fail-safe。

set -u

if [ "$#" -eq 0 ]; then
    printf '%s\n' "herdr-popup-run: no command given" >&2
    exit 2
fi

# Ctrl-C 相当。zsh 側の EXIT_CODE_SIGINT(=130) と同じ値をここで持つ
# （managed.zsh の定数は zsh セッション内にしか無く bash からは参照できない）。
readonly HERDR_POPUP_EXIT_SIGINT=130

# popup は PATH を剥ぎ取られ LANG も欠けることがある。欠けると zsh の ${#x} が
# バイト単位になり多バイトが壊れる。子へ渡す前にここで一度だけ補う。
export LANG="${LANG:-en_US.UTF-8}"

# p10k の gitstatus は popup PTY で setopt monitor に失敗し zsh -ilc を即死させる。
# managed.zsh がこの変数を見てテーマ初期化を飛ばす。従来 config.toml 側で
# コマンド前置きしていたものをラッパーが一括で export して吸収する。
# この変数は p10k gate 専用。pause/マーク契約とは別物（HERDR_POPUP_WRAPPED）にする —
# 混ぜると将来どこかで HERDR_POPUP_COMMAND を pause 判定に使ったとき全 popup で誤爆する。
export HERDR_POPUP_COMMAND=1

# 「エラー時 pause 機構の下で走っている」ことを示す契約変数。個別 pause 側
# （_freview_pause_if_popup 等）はこれで発火判定する。
export HERDR_POPUP_WRAPPED=1

# 個別 pause の実行を記録させるマークファイル。
pause_mark=""
if pause_mark="$(mktemp -t herdr-popup-pause 2>/dev/null)"; then
    export HERDR_POPUP_PAUSE_MARK="$pause_mark"
    # EXIT だけだと SIGTERM/SIGHUP で残骸が出る
    trap '[ -n "$pause_mark" ] && rm -f "$pause_mark"' EXIT HUP INT TERM
else
    # マークが作れなくても popup 自体は動かす。この場合ラッパーが必ず pause する
    # 側に倒れる（個別 pause と二重に待つことはあるが、閉じて読めないより良い）。
    pause_mark=""
    unset HERDR_POPUP_PAUSE_MARK
fi

# exec しない: 終了コードを見て pause 判定するのがこのラッパーの存在理由。
"$@"
command_exit=$?

# 正常終了(0)と Ctrl-C(130)は待たない。130 はピッカーのキャンセル等の正常操作を含む。
if [ "$command_exit" -eq 0 ] || [ "$command_exit" -eq "$HERDR_POPUP_EXIT_SIGINT" ]; then
    exit "$command_exit"
fi

# 個別 pause が既に待った場合はここでは待たない（二重待ちを避ける）。
if [ -n "$pause_mark" ] && [ -s "$pause_mark" ]; then
    exit "$command_exit"
fi

printf '\n' >&2
printf '%s\n' "エラーで終了しました (exit ${command_exit})。何かキーを押すと閉じます" >&2

# tty が無ければ待てない。待つと閉じられない popup になるので読み取りは省く。
# メッセージは読み取り可否に関わらず出す（テストの観測点でもある）。
if [ -t 0 ]; then
    read -rsn1 _herdr_popup_discard </dev/tty 2>/dev/null || true
    printf '\n' >&2
fi

exit "$command_exit"
