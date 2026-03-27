#!/bin/bash
# Claude Code status line — 2-line emoji layout with cost, rate limits, and worktree support

input=$(cat)

# Extract fields from JSON
model=$(echo "$input" | jq -r '.model.display_name // ""')
ctx_used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
ctx_current=$(echo "$input" | jq -r '.context_window.current_usage // empty')
ctx_tokens=$(echo "$input" | jq -r '.context_window.total_input_tokens // empty')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // empty')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // empty')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
worktree_name=$(echo "$input" | jq -r '.worktree.name // ""')
branch=$(echo "$input" | jq -r '.worktree.branch // ""')

# worktree.branch はworktreeセッション限定フィールドなので、通常セッションではgitコマンドで取得
if [ -z "$branch" ]; then
  real_cwd="${cwd/#\~/$HOME}"
  if git -C "$real_cwd" --no-optional-locks rev-parse --git-dir >/dev/null 2>&1; then
    branch=$(git -C "$real_cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null \
             || git -C "$real_cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
  fi
fi
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
five_resets=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
seven_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
seven_resets=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

# Shorten home directory to ~
cwd="${cwd/#$HOME/\~}"

# Color helper: green <70%, yellow 70-89%, red 90%+
pct_color() {
  local pct=$1
  if [ "$pct" -ge 90 ]; then
    printf '\033[31m'
  elif [ "$pct" -ge 70 ]; then
    printf '\033[33m'
  else
    printf '\033[32m'
  fi
}

# Human-readable time from unix epoch resets_at
time_until() {
  local resets_at=$1
  local now
  now=$(date +%s)
  local diff=$((resets_at - now))
  if [ "$diff" -le 0 ]; then
    printf 'now'
    return
  fi
  local days=$((diff / 86400))
  local hours=$(( (diff % 86400) / 3600 ))
  local mins=$(( (diff % 3600) / 60 ))
  if [ "$days" -ge 1 ]; then
    printf '%dd%dh' "$days" "$hours"
  else
    printf '%dh%dm' "$hours" "$mins"
  fi
}

# Human-readable token count (e.g. 12.3k, 1M)
format_tokens() {
  local n=$1
  if [ "$n" -ge 1000000 ]; then
    printf '%.1fM' "$(echo "scale=1; $n / 1000000" | bc)"
  elif [ "$n" -ge 1000 ]; then
    printf '%.1fk' "$(echo "scale=1; $n / 1000" | bc)"
  else
    printf '%d' "$n"
  fi
}

# Human-readable duration from milliseconds
format_duration_ms() {
  local ms=$1
  local total_s=$((ms / 1000))
  local hours=$((total_s / 3600))
  local mins=$(( (total_s % 3600) / 60 ))
  local secs=$((total_s % 60))
  if [ "$hours" -ge 1 ]; then
    printf '%dh%dm' "$hours" "$mins"
  elif [ "$mins" -ge 1 ]; then
    printf '%dm%ds' "$mins" "$secs"
  else
    printf '%ds' "$secs"
  fi
}

# --- Line 1: Model | Context Cost Duration | Rate limits ---

# 🤖 Model
if [ -n "$model" ]; then
  printf '\033[34m🤖 %s\033[0m' "$model"
fi

printf ' |'

# 🧠 Context used — "12.3k / 1M (45%)"
if [ -n "$ctx_used" ]; then
  ctx_int=$(printf '%.0f' "$ctx_used")
  ctx_color=$(pct_color "$ctx_int")
  # current_usageは0-1の割合なのでctx_sizeを掛けて絶対トークン数に変換
  used_tokens=""
  if [ -n "$ctx_current" ] && [ -n "$ctx_size" ]; then
    used_tokens=$(echo "$ctx_current * $ctx_size" | bc | cut -d. -f1)
  elif [ -n "$ctx_used" ] && [ -n "$ctx_size" ]; then
    used_tokens=$(echo "$ctx_used * $ctx_size / 100" | bc | cut -d. -f1)
  elif [ -n "$ctx_tokens" ]; then
    used_tokens="$ctx_tokens"
  fi
  if [ -n "$used_tokens" ] && [ -n "$ctx_size" ]; then
    used_fmt=$(format_tokens "$used_tokens")
    size_fmt=$(format_tokens "$ctx_size")
    printf " ${ctx_color}🧠 %s / %s (%s%%)\033[0m" "$used_fmt" "$size_fmt" "$ctx_int"
  else
    printf " ${ctx_color}🧠 %s%%\033[0m" "$ctx_int"
  fi
fi

# 💰 Cost (2 decimal places)
if [ -n "$cost" ]; then
  printf ' \033[97m💰 $%s\033[0m' "$(printf '%.2f' "$cost")"
fi

# ⏳ Duration
if [ -n "$duration_ms" ]; then
  dur_str=$(format_duration_ms "$duration_ms")
  printf ' \033[90m⏳ %s\033[0m' "$dur_str"
fi

# Rate limits section
if [ -n "$five_pct" ] || [ -n "$seven_pct" ]; then
  printf ' |'

  if [ -n "$five_pct" ]; then
    five_int=$(printf '%.0f' "$five_pct")
    five_color=$(pct_color "$five_int")
    reset_str=""
    if [ -n "$five_resets" ]; then
      reset_str=" ↻$(time_until "$five_resets")"
    fi
    printf " ${five_color}🕰️ %s%%%s\033[0m" "$five_int" "$reset_str"
  fi

  if [ -n "$seven_pct" ]; then
    seven_int=$(printf '%.0f' "$seven_pct")
    seven_color=$(pct_color "$seven_int")
    reset_str=""
    if [ -n "$seven_resets" ]; then
      reset_str=" ↻$(time_until "$seven_resets")"
    fi
    printf " ${seven_color}📅 %s%%%s\033[0m" "$seven_int" "$reset_str"
  fi
fi

echo

# --- Line 2: Directory + Branch + Worktree ---

printf '\033[33m📂 %s\033[0m' "$cwd"

if [ -n "$branch" ]; then
  printf ' \033[35m🌿 %s\033[0m' "$branch"
fi

if [ -n "$worktree_name" ]; then
  printf ' \033[36m🌲 %s\033[0m' "$worktree_name"
fi

echo
