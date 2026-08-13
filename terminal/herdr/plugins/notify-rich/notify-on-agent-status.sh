#!/bin/zsh
# Herdr hook for agent-status, agent-detection, and pane-focus events. Status events
# replace Herdr's plain OS toast with this repository's rich Mac notification;
# every supported event refreshes auto-managed tab labels with an AI identifier and
# status icon, plus the conversation title for claude only (see the agent=="claude"
# check in title_usable below — codex keeps its identifier/status icon but not the
# conversation-title label).
# Gemini is excluded entirely (see the agent=="gemini" guard below) and handled by
# its own hooks instead.
# pane.focused additionally clears the SHELL-owned ✅/❌ status icon for that tab
# (clear_herdr_shell_status_state): focusing a tab means the user saw the completion
# or failure, so it is dropped instead of lingering until the next command starts.
# That block sits BEFORE the gemini guard (shell state is agent-independent) and
# before the label-rebuild block (a rebuild reading the pre-clear label would write
# the glyph back). ✋ input-wait is deliberately NOT cleared — it is a live state.
#
# Deliberately no `set -e`: a failed lookup should fall back to "no notification",
# never abort mid-way and leave the agent silently un-notified (same policy as
# ai/claude/hooks/stop-send-notification.sh).

REPO_ROOT="${SET:-$HOME/Desktop/repository/SettingFiles}"

# herdrのstripped envではLANGが未設定になり得て、zshの${#x}やスライスがバイト単位に
# なりUTF-8ラベル/通知本文が壊れる（codex-stop-notification.shと同じ対策）。
export LANG="${LANG:-en_US.UTF-8}"

# Herdrは[[events]]フックを[[keys.command]]と同じstripped PATH（Homebrewなし）で
# 起動する。通常配信はHERDR_BIN_PATHのnotification APIを使うが、API失敗時の
# terminal-notifierフォールバック用にHomebrew binを末尾追加。テストのfake_binや
# 通常シェルのPATH優先順位は変えない。
case ":$PATH:" in
  *:/opt/homebrew/bin:*) ;;
  *) export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin" ;;
esac

# Herdr injects IDs into each event; status and detection events also include agent data.
event_json="${HERDR_PLUGIN_EVENT_JSON:-}"
event_kind="${HERDR_PLUGIN_EVENT:-}"
[[ -z "$event_kind" ]] \
  && event_kind="$(print -r -- "$event_json" | jq -r '.event // empty' 2>/dev/null)"
agent="$(print -r -- "$event_json" \
  | jq -r '.data.agent // .data.pane.agent // empty' 2>/dev/null)"
# `status` is a read-only zsh special parameter (last exit code) — use agent_status instead.
agent_status="$(print -r -- "$event_json" \
  | jq -r '.data.agent_status // .data.pane.agent_status // empty' 2>/dev/null)"

# Gemini has no official Herdr installer integration, so its agent_status is derived
# solely from Herdr's screen-manifest detection and oscillates done<->working<->idle,
# firing this plugin many times per response (tab renames included). Gemini therefore
# opts OUT of the notify-rich single-source model entirely (notification AND tab
# rename) and notifies via its own AfterAgent/Notification tmux hooks
# (ai/gemini/hooks/notification.sh, HERDR guard relaxed there). Claude/Codex report
# status accurately via their installers and stay managed by this plugin.
#
# Conversation-title tab labeling (see title_usable below) is claude-only: codex also
# sets terminal_title_stripped to a conversation summary, but that summary is far less
# meaningful for codex tabs, so codex keeps only its identifier emoji + status icon
# (e.g. 🪷🤖1) instead of having the label replaced by the conversation title.
#
# The notification BODY is likewise agent-split: claude uses terminal_title_stripped
# as-is, codex replaces it with a transcript-derived summary (same build_session_summary
# format as the tmux hooks) resolved via agent_session.value == codex session_id —
# see the notify_body block below. Codex's choice prompts fire no codex hook, so this
# plugin must stay codex's single notifier under Herdr; only the body text is enriched.

herdr_bin="${HERDR_BIN_PATH:-herdr}"
pane_id="${HERDR_PANE_ID:-}"
[[ -z "$pane_id" ]] \
  && pane_id="$(print -r -- "$event_json" \
    | jq -r '.data.pane_id // .data.pane.pane_id // empty' 2>/dev/null)"
[[ -z "$pane_id" ]] && exit 0

# 両イベントで同じ最新pane情報を使い、タブ名更新と通知本文の取得経路を一本化する。
pane_json="$("$herdr_bin" pane get "$pane_id" 2>/dev/null)"
[[ -z "$pane_json" ]] && exit 0

[[ -z "$agent" ]] \
  && agent="$(print -r -- "$pane_json" | jq -r '.result.pane.agent // empty' 2>/dev/null)"

# タブをfocusした＝シェルの完了✅/失敗❌を見たので確認済みとして落とす。
# gemini guardより前に置くのは意図的: このクリアはシェル所有の状態が対象で、
# そのタブでどのAIが動いているかとは無関係。geminiがnotify-richの通知/ラベル
# 再構築からoptoutしていても、シェルのアイコンは同じ契機で消えるべき。
# 既存のラベル再構築ブロックより前に置くのも必須で、後ろだとクリア前のラベルを
# 読んだ再構築が状態グリフを書き戻してしまう。
# ✋（応答待ち）は対象外: 生きた状態なのでclear側がマーカーを見て自制する。
# state不在ならstat 1回でreturnするので、頻発するfocusイベントでも実質無コスト。
tab_id="$(print -r -- "$pane_json" | jq -r '.result.pane.tab_id // empty' 2>/dev/null)"
# シェル所有✋マーカーのread（_herdr_shell_status_marker_read）と、focusクリアの
# clear_herdr_shell_status_stateを読み込む。
# fail-safe: 読み込めなくてもピン留めとfocusクリアが無効になるだけで処理は続行する。
source "${REPO_ROOT}/shell/tmux/herdr_status_icon.sh" 2>/dev/null || true
case "$event_kind" in
  pane.focused|pane_focused)
    if [[ -n "$tab_id" ]] && (( ${+functions[clear_herdr_shell_status_state]} )); then
      clear_herdr_shell_status_state "$tab_id" "${HERDR_WORKSPACE_ID:-}" || true
    fi
    ;;
esac

[[ "$agent" == "gemini" ]] && exit 0

source "${REPO_ROOT}/shell/tmux/tmux_emoji.conf"
# 通知音マップ（ai_notification_sound <event>）。tmux経路の共通ヘッダと同じ定義を共有し、
# イベント種別（done→completed / blocked→waiting）で音を決める（全AI共通）。
source "${REPO_ROOT}/shell/tmux/ai_notification_sound.sh"
# APIエラー通知のburst抑止（tmux経路 stop-send-notification.sh と共有）。
source "${REPO_ROOT}/shell/tmux/ai_notification_burst_guard.sh" 2>/dev/null || true

managed_label_state_file() {
  local tab_id="$1"
  local state_root="${HERDR_PLUGIN_STATE_DIR:-}"
  local session_key="${HERDR_SOCKET_PATH:-default}"
  local tab_key="$tab_id"

  [[ -z "$state_root" || -z "$tab_key" ]] && return 1
  session_key="${session_key//[^A-Za-z0-9._-]/_}"
  tab_key="${tab_key//[^A-Za-z0-9._-]/_}"
  print -r -- "${state_root}/tab-labels/${session_key}/${tab_key}"
}

# 表示名を最大10文字に丸める。超過時のみ先頭10文字に「..」を付す。
# zshの ${str[1,10]} はマルチバイト1文字=1カウントなので日本語もそのまま切れる
# （タブ処理ブロックの会話概要truncate ${title_text[1,20]} と同じ挙動）。
truncate_display_name() {
  local str="$1"
  if (( ${#str} > 10 )); then
    print -r -- "${str[1,10]}.."
  else
    print -r -- "$str"
  fi
}

case "$agent" in
  claude) id_emoji="$EMOJI_ID_CLAUDE" ;;
  codex)  id_emoji="$EMOJI_ID_CODEX" ;;
  gemini) id_emoji="$EMOJI_ID_GEMINI" ;;
  *)      id_emoji="🤖" ;;
esac

title_text="$(print -r -- "$pane_json" | jq -r '.result.pane.terminal_title_stripped // empty' 2>/dev/null)"
session_id="$(print -r -- "$pane_json" | jq -r '.result.pane.agent_session.value // empty' 2>/dev/null)"
[[ -z "$title_text" ]] && title_text="(no title)"

# ラベル解析成功時だけ1（非エディタ由来）へ更新する。未計算・解析失敗は2として
# タブrenameと会話title採用を止め、通知本文も採用済みstateへfail-closedする。
editor_title_rc=2
last_auto_label=""

# タブ名先頭にAI識別子+状態アイコンを付与する（tmuxのwindow名アイコンと同じ思想）。
# working=進行中🤖 blocked=入力待ち✋ done=完了✅、idle(既読)/unknown(AI未検出)は
# アイコンを外して元のラベルに戻す。集約状態は `tab get` の agent_status（タブ内
# 複数paneがあってもHerdrが1つに集約済み）を使い、識別子だけ発火paneのagentを使う。
# tab_idはfocusクリアのため冒頭で解決済み（gemini guardの前）。
# screen_label生成（後段）でも参照するため、タブ処理ブロック未到達（tab_id/tab_json
# が空）でも未定義参照にならないよう既定値を先出しする。真になるのはブロック内で
# base_labelを会話概要20字truncateに置き換えた時だけ。
record_auto_label=false
if [[ -n "$tab_id" ]]; then
  tab_json="$("$herdr_bin" tab get "$tab_id" 2>/dev/null)"
  if [[ -n "$tab_json" ]]; then
    tab_status="$(print -r -- "$tab_json" | jq -r '.result.tab.agent_status // empty' 2>/dev/null)"
    current_label="$(print -r -- "$tab_json" | jq -r '.result.tab.label // empty' 2>/dev/null)"

    # herdr-automatic-rename owns the exact `[1-9] ` jump-key prefix. Keep it
    # outside notify-rich's identifier/status/base-label state machine.
    index_prefix=""
    label_body="$current_label"
    if [[ "$label_body" == \[[1-9]\]\ * ]]; then
      index_prefix="${label_body[1,4]}"
      label_body="${label_body[5,-1]}"
    fi

    status_emoji=""
    case "$tab_status" in
      working) status_emoji="$EMOJI_STATUS_ONGOING" ;;
      blocked) status_emoji="$EMOJI_STATUS_NOTIFICATION" ;;
      done)    status_emoji="$EMOJI_STATUS_COMPLETED" ;;
    esac

    # 絵文字除去、ラベル/タイトルのHerdr既定判定、エディタ由来判定を1 Python
    # processへ統合する。stdoutはshell-safeな固定名代入だけ。終了状態・値契約の
    # どちらかが壊れたらrenameせず、通知処理自体は後段fallbackで継続する。
    base_label="$label_body"
    label_analysis_ok=false
    unset BASE_LABEL BASE_IS_DEFAULT TITLE_IS_DEFAULT EDITOR_TITLE_RC
    analysis_output="$(python3 "${REPO_ROOT}/shell/tmux/tmux_window_name.py" \
      analyze-herdr-label "$label_body" "$title_text" 2>/dev/null)"
    analysis_status=$?
    if (( analysis_status == 0 )) && eval "$analysis_output" 2>/dev/null \
       && [[ -n "${BASE_LABEL+x}" ]] \
       && [[ "$BASE_IS_DEFAULT" == 0 || "$BASE_IS_DEFAULT" == 1 ]] \
       && [[ "$TITLE_IS_DEFAULT" == 0 || "$TITLE_IS_DEFAULT" == 1 ]] \
       && [[ "$EDITOR_TITLE_RC" == 0 || "$EDITOR_TITLE_RC" == 1 ]]; then
      base_label="$BASE_LABEL"
      editor_title_rc="$EDITOR_TITLE_RC"
      label_analysis_ok=true
    fi
    state_file="$(managed_label_state_file "$tab_id")"
    # stateは2行: 1行目=採用済み概要、2行目=採用時のclaude session_id
    # (agent_session.value)。HerdrのタブIDはサーバー再起動でカウンターが
    # リセットされ再利用されるため、session照合なしで復元すると無関係な
    # 新規タブに過去セッションの概要ラベルが付いてしまう。
    state_session_id=""
    if [[ -n "$state_file" && -f "$state_file" ]]; then
      { IFS= read -r last_auto_label; IFS= read -r state_session_id; } \
        < "$state_file" 2>/dev/null
    fi

    herdr_default_label=false
    auto_managed=false
    if [[ "$label_analysis_ok" == true && "$BASE_IS_DEFAULT" == 1 ]]; then
      herdr_default_label=true
      auto_managed=true
    elif [[ "$label_analysis_ok" == true && -n "$last_auto_label" \
            && "$base_label" == "$last_auto_label" ]]; then
      auto_managed=true
    fi

    # タイトルを会話概要とみなせるのはclaudeのみ。CodexもターミナルタイトルにAI
    # 会話概要をセットするが、タブ名への反映は claude 限定にする（codexは識別絵文字
    # ＋状態アイコンのみ維持）。非AI paneのタイトルはNvim等が任意の値
    # （COMMIT_EDITMSG等）をセットするため、いずれにせよタブ名には採用しない。
    # claude paneでも$EDITOR実行中はタイトルの著者がnvimになるため、発信元判定
    # （is-editor-set-title、上で計算済みのeditor_title_rc）でも絞る。
    # is-herdr-default-labelの`!`否定と違いrc==1の明示比較なのは意図的な非対称:
    # あちらはfalse側に倒れても「デフォルトラベル扱いされない」だけで無害だが、
    # こちらはfalse側に倒れると汚染タイトルが素通りするため、python3クラッシュ等の
    # 判定不能も不採用側に倒す（fail-closed）。
    title_usable=false
    if [[ "$label_analysis_ok" == true \
          && "$agent" == "claude" && "$title_text" != "(no title)" ]] \
       && (( TITLE_IS_DEFAULT == 0 )) \
       && (( editor_title_rc == 1 )); then
      title_usable=true
    fi

    record_auto_label=false
    if [[ "$auto_managed" == true && "$title_usable" == true ]]; then
      base_label="${title_text[1,20]}"
      record_auto_label=true
    elif [[ "$herdr_default_label" == true && -n "$last_auto_label" ]]; then
      if [[ -n "$session_id" && "$state_session_id" == "$session_id" ]]; then
        # 同一claudeセッション中の一時的なデフォルトラベル復帰のみ復元する。
        base_label="$last_auto_label"
      else
        # session不一致（再利用タブID・旧1行形式含む）は過去セッションの概要
        # なので復元しない。タブ内にagentが居ない時（unknown/空）だけstateを
        # stale として自己削除する。idle/working等は別paneのclaudeが所有して
        # いる可能性があるため温存する（✋マーカーのstale自己削除と同じ思想）。
        case "$tab_status" in
          working|blocked|done|idle) ;;
          *) rm -f -- "$state_file" 2>/dev/null ;;
        esac
      fi
    fi
    if [[ "$label_analysis_ok" == true && -n "$status_emoji" ]]; then
      new_label="${id_emoji}${status_emoji}${base_label}"
    elif [[ "$label_analysis_ok" == true ]]; then
      new_label="${base_label}"
    fi

    # シェルが入力待ち✋を所有している間（マーカー存在中）は状態グリフを✋に
    # ピン留めする（優先度はworkspace集約と同じ ✋>❌>🤖>✅）。ベース名の会話概要
    # 追従はそのまま活きる（compute-updated-labelは識別子と本文を保持する）。
    # 空代入ガード必須: python3失敗時に空ラベルへrenameしないため。
    if [[ "$label_analysis_ok" == true ]] \
       && (( ${+functions[_herdr_shell_status_marker_read]} )); then
      marker_glyph="$(_herdr_shell_status_marker_read "$tab_id" 2>/dev/null)"
      if [[ -n "$marker_glyph" ]]; then
        pinned_label="$(python3 "${REPO_ROOT}/shell/tmux/tmux_window_name.py" \
          compute-updated-label "$new_label" "$marker_glyph" 2>/dev/null)"
        [[ -n "$pinned_label" ]] && new_label="$pinned_label"
      fi
    fi

    rename_ok=true
    if [[ "$label_analysis_ok" == true ]]; then
      new_label="${index_prefix}${new_label}"
    fi
    if [[ "$label_analysis_ok" == true && "$new_label" != "$current_label" ]] \
       && ! "$herdr_bin" tab rename "$tab_id" "$new_label" >/dev/null 2>&1; then
      rename_ok=false
    fi

    # 概要が変わった時に加え、session_idの差分だけでも書き直す（旧1行stateの
    # 2行化と、同ラベルのまま別セッションへ移った場合の所有者更新のため）。
    if [[ "$label_analysis_ok" == true \
          && "$record_auto_label" == true && "$rename_ok" == true \
          && -n "$state_file" ]] \
       && [[ "$base_label" != "$last_auto_label" \
             || "$session_id" != "$state_session_id" ]]; then
      state_dir="${state_file:h}"
      if mkdir -p "$state_dir" 2>/dev/null; then
        { print -r -- "$base_label"; print -r -- "$session_id"; } >| "$state_file" 2>/dev/null
      fi
    fi
  fi
fi

# Only completed (done) or awaiting input (blocked) are worth a notification.
# idle = already-seen completion, working/unknown = nothing to report yet.
case "$event_kind" in
  pane.agent_status_changed|pane_agent_status_changed) ;;
  *) exit 0 ;;
esac
case "$agent_status" in
  done|blocked) ;;
  *) exit 0 ;;
esac

# claudeのdoneはターン終了ごとに発火するが、async Agentの完了待ちやScheduleWakeup
# 武装中は会話がまだ継続する（ハーネスが再起動する）ため、tmux経路の
# stop-send-notification.shと同じPENDING_BACKGROUND_WORK判定（claude_transcript_
# analyze.py）で完了通知を抑止する。tmux経路はHERDR_ENVガードで即exitするため、
# Herdr下ではこのプラグインが同じガードを持つ必要がある。
# transcriptはagent_session.value（claudeのsession_id）から解決する。
# サブシェル格納の理由はcodex_summaryブロックと同じfail-safe: transcript未解決・
# 解析失敗は空出力に落ち、従来どおり通知する（通知が完全に死ぬ事故を避ける）。
# 出力は3行: PENDING_BACKGROUND_WORK / LAST_TURN_API_ERROR / LAST_TURN_API_ERROR_TEXT。
# エラー本文（3行目）は改行やコロン等の任意文字を含みうるため、区切り文字方式ではなく
# 「残り全部を最後の行として読む」行ベースで受け取る（呼び出し側のIFS= read -r ×2 +
# cat参照）。fail-safe: 途中で失敗すれば空出力に落ち、呼び出し側は全変数が空のまま
# 従来どおり通常の完了通知にフォールバックする。
if [[ "$agent" == "claude" && "$agent_status" == "done" ]]; then
  claude_pending="$(
    source "${REPO_ROOT}/shell/tmux/ai_notification_summary.sh" 2>/dev/null || exit 0
    transcript="$(resolve_host_transcript "$session_id")" || exit 0
    analysis="$(python3 "${REPO_ROOT}/shell/tmux/claude_transcript_analyze.py" "$transcript" 2>/dev/null)"
    [[ $? -ne 0 || -z "$analysis" ]] && exit 0
    eval "$analysis"
    print -r -- "${PENDING_BACKGROUND_WORK:-0}"
    print -r -- "${LAST_TURN_API_ERROR:-}"
    print -r -- "${LAST_TURN_API_ERROR_TEXT:-}"
  )"
  # $(...)は末尾改行を除去するため、空行が続くケース（エラーなし等）だと
  # パターンマッチ(%%$'\n'*)が「改行なし=1行しかない」と誤認識し、後続フィールドの
  # 値が前のフィールドに漏れる（例: "0"だけ残るとPENDING_BACKGROUND_WORKの値が
  # error種別として誤読される）。read -r ×3行での行単位パースなら空行も正しく
  # 独立したフィールドとして読める。
  { IFS= read -r claude_pending_flag
    IFS= read -r claude_api_error
    IFS= read -r claude_api_error_text
  } <<< "$claude_pending"
  [[ "$claude_pending_flag" == "1" && -z "$claude_api_error" ]] && exit 0
fi

# Workspace display name isn't in the context JSON; resolve it with one `workspace list` call.
ws_id="${HERDR_WORKSPACE_ID:-}"
ws_label=""
if [[ -n "$ws_id" ]]; then
  ws_label="$("$herdr_bin" workspace list 2>/dev/null \
    | jq -r --arg w "$ws_id" '.result.workspaces[]? | select(.workspace_id==$w) | .label // empty' 2>/dev/null)"
fi

# herdr-automatic-rename also decorates workspace labels. Notification context
# shows the stable workspace name, not the jump key that changes with ordering.
if [[ "$ws_label" == \[[1-9]\]\ * ]]; then
  ws_label="${ws_label[5,-1]}"
fi

# screen_label shows workspace名:tab名. tab名はタブ処理ブロックで確定した装飾除去後の
# base_label（claudeは会話概要、それ以外は素のタブ名）。どちらか取れなければ丸ごと省略。
# ただしtab名が会話概要由来（record_auto_label==true: claude+概要採用）の場合は、
# 通知本文(title_text)と内容が被るため ":tab名" を省き 🖥️ws名 だけにする。手動ラベルや
# codex等（record_auto_label==false）は被らないため従来どおり ":tab名" を残す。
tab_base="${base_label:-}"
screen_label=""
if [[ -n "$ws_label" && -n "$tab_base" ]]; then
  if [[ "${record_auto_label:-false}" == true ]]; then
    screen_label=" 🖥️$(truncate_display_name "$ws_label")"
  else
    screen_label=" 🖥️$(truncate_display_name "$ws_label"):$(truncate_display_name "$tab_base")"
  fi
fi

# id_emoji は冒頭のタブアイコン処理で既に決定済み。ここでは通知本文用の
# status_emoji/label_text（done/blocked専用の日本語ラベル）と通知音イベントを再定義する。
# ここに到達する時点で agent_status は done/blocked のいずれか（237-240行でそれ以外はexit済み）。
# 音はイベント種別で決まる（done=完了→completed / blocked=入力待ち→waiting、tmux経路と共通）。
case "$agent_status" in
  done)
    status_emoji="$EMOJI_STATUS_COMPLETED"
    label_text="完了"
    sound_event="completed"
    ;;
  blocked)
    status_emoji="$EMOJI_STATUS_NOTIFICATION"
    label_text="入力待ち"
    sound_event="waiting"
    ;;
esac

# claude+doneでtranscript末尾がAPIエラーの場合、通常の完了見た目をエラー停止用に
# 上書きする（tmux経路 stop-send-notification.sh の❌エラー停止分岐と体裁を揃える）。
# burst抑止も同じ関数を使い、同一セッション・同一エラー種別の短時間再通知を防ぐ。
api_error_notify_body=""
if [[ "$agent" == "claude" && -n "${claude_api_error:-}" ]]; then
  if ! api_error_burst_should_suppress "$session_id" "$claude_api_error" "$(date +%s)" 60; then
    status_emoji="$EMOJI_STATUS_ERROR"
    label_text="エラー停止"
    sound_event="error"
    api_error_notify_body="${claude_api_error_text:-エラー種別: ${claude_api_error}}"
  else
    exit 0
  fi
fi

# 通知本文: claudeはterminal_title_stripped（会話概要として有意味）をそのまま使う。
# codexはそのタイトルが無意味なため、agent_session.value（codexのsession_id、
# herdr-agent-state.shがSessionStartのhook入力から報告）でtranscriptを解決し、
# tmuxフックと同じbuild_session_summary形式の概要に差し替える。
# サブシェルに閉じ込める理由: setopt bsd_echo（zsh builtin echoの\n展開抑止）と、
# evalされる解析変数・sourceされる要約関数群を本体の名前空間に漏らさないため。
# あらゆる失敗（jq/python3不在・transcript未解決・メッセージ0件）は空出力に落ち、
# 従来のtitle_text本文へフォールバックする（no set -e方針と同じfail-safe）。
notify_body="$title_text"
# claude: 外部エディタがタイトルを所有中（editor_title_rc==0、判定不能もfail-closedで
# 同扱い）はtitle_textがファイル名なので、採用済み概要（state fileのlast_auto_label、
# タブ処理ブロックで読込済み）へフォールバックする。無ければ"(no title)"。
if [[ "$agent" == "claude" ]] && (( editor_title_rc != 1 )); then
  notify_body="${last_auto_label:-(no title)}"
fi
if [[ "$agent" == "codex" && -n "$session_id" ]]; then
  codex_summary="$(
    setopt bsd_echo 2>/dev/null
    analysis="$(jq -n --arg sid "$session_id" '{session_id: $sid}' 2>/dev/null \
      | python3 "${REPO_ROOT}/ai/codex/hooks/codex_hook_common.py" analyze 2>/dev/null)"
    [[ $? -ne 0 || -z "$analysis" ]] && exit 0
    eval "$analysis"
    source "${REPO_ROOT}/shell/tmux/ai_notification_summary.sh" 2>/dev/null || exit 0
    # blocked（herdr検知の入力待ち）と、doneでもアシスタントが質問で終えた場合は
    # tmuxの✋応答待ちと同じく最終アシスタントメッセージを出す。それ以外の完了は
    # タスク種別絵文字＋最終ユーザーメッセージ（tmuxの✅終了と同形式）。
    if [[ "$agent_status" == "blocked" || "${WAITING_FOR_USER_RESPONSE:-}" == "true" ]]; then
      build_session_summary "✋" "${LAST_ASSISTANT_MESSAGE:-}" \
        "${USER_MESSAGE_COUNT:-0}" "${SESSION_DURATION_FORMATTED:-}"
    else
      build_session_summary "$(guess_task_type_emoji "${LAST_USER_MESSAGE:-}")" \
        "${LAST_USER_MESSAGE:-}" "${USER_MESSAGE_COUNT:-0}" "${SESSION_DURATION_FORMATTED:-}"
    fi
  )"
  [[ -n "$codex_summary" ]] && notify_body="$codex_summary"
fi
# APIエラー本文は上記どちらの分岐よりも優先する（エラー種別・内容を確実に伝えるため）
[[ -n "$api_error_notify_body" ]] && notify_body="$api_error_notify_body"

agent_label="${agent:0:1:u}${agent:1}"
now="$(date '+%H:%M:%S')"
title="${id_emoji}${status_emoji} ${agent_label}${label_text}${screen_label} 🕰️${now}"

group=""
if [[ -n "$agent" && -n "$session_id" ]]; then
  group="${agent}-${session_id}"
fi

# Homebrew terminal-notifier 2.0.0 is unsigned and can return success while modern macOS
# silently suppresses it. Herdr is the stable notification identity and honors
# [ui.toast] delivery="system". Keep terminal-notifier only as an API-failure fallback.
# Exit code alone is not enough: "notification show" exits 0 even when
# [ui.toast] delivery="off" suppresses delivery (response body has shown:false),
# so the fallback below was unreachable while toast delivery stayed disabled.
case "${sound_event:-completed}" in
  completed) herdr_sound="done" ;;
  *) herdr_sound="request" ;;
esac
herdr_notify_response="$("$herdr_bin" notification show "$title" --body "$notify_body" \
  --sound "$herdr_sound" 2>/dev/null)"
if [[ $? -eq 0 ]] \
   && print -r -- "$herdr_notify_response" | jq -e '.result.shown == true' >/dev/null 2>&1; then
  exit 0
fi

source "${REPO_ROOT}/shell/zsh/alias/notification.zsh"

# NOTIFY_NO_DECORATE: this pane is outside tmux, so notify()'s auto tmux-label
# decoration would be a no-op anyway, but it also strips our own time suffix —
# suppress it since we build the full title (including time) ourselves.
# NOTIFY_FORCE: bypass AI-session suppression; this fallback intentionally notifies.
NOTIFY_NO_DECORATE=1 NOTIFY_FORCE=1 notify "$title" "$notify_body" "$(ai_notification_sound "${sound_event:-completed}")" "$group"
