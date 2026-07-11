# Geminiトランスクリプト(JSON/JSONL)の一括抽出クエリ。
# ai/gemini/hooks/notification.sh から `jq -s -r -f` で呼ばれ、通知要約に必要な
# 値を @sh クォート済みの1行（フック側で eval）として出力する。
# 時間計算（セッション時間/JST完了時刻）もここで行い、旧実装のbashヘルパー
# format_session_duration / format_completion_time_jst の date 起動×4を削減する。
# パリティ仕様は tests/test_gemini_transcript_summary.py が固定する。
#
# 時間計算のパリティ根拠: 旧bashヘルパーはTZなしローカルパース→ローカル表示で
# マシンTZが相殺される。jqの strptime/mktime/gmtime はUTCパース→UTC表示で
# 同様に相殺されるため、naive演算として出力が完全一致する（+9hでJST表示）。

# ISO8601先頭19文字（秒まで）をepochへ。不正・欠落は null（bash側の空文字劣化と同義）
def to_epoch: try (tostring | .[0:19] | strptime("%Y-%m-%dT%H:%M:%S") | mktime) catch null;

# tmux_notification_title.sh の format_duration と同一フォーマット（1h1m / 1m2s / 5s）
def fmt_dur:
  (. / 3600 | floor) as $h | ((. % 3600) / 60 | floor) as $m | (. % 60) as $s |
  if $h > 0 then "\($h)h\($m)m" elif $m > 0 then "\($m)m\($s)s" else "\($s)s" end;

# 単一オブジェクト形式（{startTime, lastUpdated, messages:[...]}）と
# $setレコードを含むslurp配列形式（レコード自体がメッセージ列）の両対応
(if (length == 1 and (.[0].messages | type) == "array") then .[0].messages else . end) as $msgs |
(if (.[0].startTime != null) then .[0].startTime else null end) as $start |
(if (length == 1 and (.[0].messages | type) == "array") then .[0].lastUpdated else ((map(select(."$set" != null and ."$set".lastUpdated != null)) | last | ."$set".lastUpdated) // .[0].lastUpdated) end) as $end |
($msgs | map(select(.type == "user" and (
  ((.content | type) == "array" and .content[-1].text != null) or
  ((.displayContent | type) == "array" and .displayContent[-1].text != null) or
  ((.content | type) == "string")
)))) as $user_msgs |
($user_msgs | length) as $count |
(if $count > 0 then
  if ($user_msgs[-1].displayContent != null and ($user_msgs[-1].displayContent | type) == "array" and ($user_msgs[-1].displayContent | length) > 0) then
    $user_msgs[-1].displayContent[-1].text
  elif ($user_msgs[-1].content != null and ($user_msgs[-1].content | type) == "array" and ($user_msgs[-1].content | length) > 0) then
    $user_msgs[-1].content[-1].text
  elif ($user_msgs[-1].content | type) == "string" then
    $user_msgs[-1].content
  else
    ""
  end
 else
  ""
 end) as $last_msg |
($end | to_epoch) as $end_epoch |
($start | to_epoch) as $start_epoch |
(if $end_epoch != null then ($end_epoch + 32400 | gmtime | strftime("%H:%M:%S")) else "" end) as $completion |
(if $end_epoch != null and $start_epoch != null then (($end_epoch - $start_epoch) | fmt_dur) else "" end) as $duration |
@sh "START_TIME=\($start) END_TIME=\($end) USER_COUNT=\($count) LAST_MSG=\($last_msg) SESSION_DURATION_FORMATTED=\($duration) COMPLETION_TIME_JST=\($completion)"
