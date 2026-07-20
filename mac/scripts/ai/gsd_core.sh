#!/bin/zsh

function _normalize_codex_gsd_hooks() {
  local source_hooks="$1"
  local normalized_hooks="$2"
  local expected_home="${3:-$HOME}"

  jq --sort-keys --arg expected_home "$expected_home" '
    def is_portable_gsd_hook:
      type == "object"
      and ((.command? // null) | type) == "string"
      and (.command | test("^node ~/.codex/hooks/gsd-[^/[:space:]]+\\.js$"));

    def hook_key($group):
      {group: ($group | del(.hooks)), hook: .} | tojson;

    def dedupe_gsd_groups:
      reduce .[] as $group (
        {seen: [], groups: []};
        if (($group.hooks? // null) | type) != "array" then
          .groups += [$group]
        else
          .seen as $seen
          | (reduce $group.hooks[] as $hook (
               {seen: $seen, hooks: []};
               if ($hook | is_portable_gsd_hook) then
                 ($hook | hook_key($group)) as $key
                 | if (.seen | index($key)) != null then .
                   else .seen += [$key] | .hooks += [$hook]
                   end
               else
                 .hooks += [$hook]
               end
             )) as $group_state
          | .seen = $group_state.seen
          | if ($group_state.hooks | length) > 0 or ($group.hooks | length) == 0 then
              .groups += [$group | .hooks = $group_state.hooks]
            else .
            end
        end
      )
      | .groups;

    walk(
      if type == "object"
        and ((.command? // null) | type) == "string"
        and (.command | test("^\\\"/[^\\\"]*/node\\\" \\\"[^\\\"]*/\\.codex/hooks/gsd-[^\\\"]+\\.js\\\"$"))
      then (.command | capture("^\\\"(?<node>/[^\\\"]*/node)\\\" \\\"(?<hook>[^\\\"]*/\\.codex/hooks/(?<script>gsd-[^\\\"/]+\\.js))\\\"$")) as $parts
        | if $parts.hook == ($expected_home + "/.codex/hooks/" + $parts.script)
        then .command = "node ~/.codex/hooks/\($parts.script)"
        else .
        end
      else .
      end
    )
    | if ((.hooks? // null) | type) == "object" then
        .hooks |= with_entries(.value |= dedupe_gsd_groups)
      else .
      end
  ' "$source_hooks" > "$normalized_hooks"
}

function _gsd_trash_artifact() {
  local artifact="$1"

  if [[ -n "$artifact" && ( -e "$artifact" || -L "$artifact" ) ]]; then
    if ! trash "$artifact"; then
      echo "Warning: failed to move temporary GSD artifact to Trash: $artifact" >&2
      return 1
    fi
  fi

  return 0
}

function _gsd_atomic_replace() {
  /bin/mv -f "$1" "$2"
}

function _restore_managed_codex_gsd_hooks() {
  local repo_root="${1:-$Repo}"
  local gsd_home="${2:-$HOME}"
  local managed_hooks="${repo_root%/}/ai/codex/hooks.json"
  local live_hooks="$gsd_home/.codex/hooks.json"
  local live_target=""
  local live_dir="${live_hooks:h}"
  local live_name="${live_hooks:t}"
  local live_normalized=""
  local managed_normalized=""
  local comparison_rc=0
  local cleanup_rc=0
  local transaction_rc=0
  local rollback_rc=0
  local switched=0
  local replacement_link="$live_dir/.${live_name}.gsd-managed-link.$$.$RANDOM"
  local backup_file=""

  if [[ -z "$repo_root" || ! -f "$managed_hooks" ]]; then
    echo "Error: managed Codex hooks file is unavailable: $managed_hooks" >&2
    return 1
  fi

  if [[ -L "$live_dir" ]]; then
    echo "Error: Codex hooks directory is an unexpected symlink: $live_dir" >&2
    return 1
  elif [[ -L "$live_hooks" ]]; then
    live_target="$(readlink "$live_hooks")"
    if [[ "$live_target" != "$managed_hooks" ]]; then
      echo "Error: Codex hooks use an unexpected symlink target: $live_target" >&2
      return 1
    fi
    return 0
  elif [[ ! -f "$live_hooks" ]]; then
    echo "Error: GSD Core did not create Codex hooks: $live_hooks" >&2
    return 1
  fi

  require_ai_setup_command jq || return 1
  require_ai_setup_command trash || return 1

  live_normalized="$(mktemp "${TMPDIR:-/tmp}/gsd-codex-live-hooks.XXXXXX")" || return 1
  managed_normalized="$(mktemp "${TMPDIR:-/tmp}/gsd-codex-managed-hooks.XXXXXX")" || {
    _gsd_trash_artifact "$live_normalized" || true
    return 1
  }

  {
    if ! _normalize_codex_gsd_hooks "$live_hooks" "$live_normalized" "$gsd_home" \
      || ! jq --sort-keys . "$managed_hooks" > "$managed_normalized"; then
      echo "Error: failed to normalize Codex GSD hooks for comparison." >&2
      comparison_rc=1
    elif ! cmp -s "$live_normalized" "$managed_normalized"; then
      echo "Error: installed Codex hooks differ from the portable managed hook set; preserving $live_hooks for review." >&2
      comparison_rc=1
    fi
  } always {
    _gsd_trash_artifact "$live_normalized" || cleanup_rc=1
    _gsd_trash_artifact "$managed_normalized" || cleanup_rc=1
  }

  (( comparison_rc == 0 && cleanup_rc == 0 )) || return 1

  if [[ -e "$replacement_link" || -L "$replacement_link" ]]; then
    echo "Error: temporary Codex hooks link already exists: $replacement_link" >&2
    return 1
  fi

  backup_file="$(mktemp "$live_dir/.${live_name}.gsd-backup.XXXXXX")" || return 1
  {
    if ! /bin/cp -p "$live_hooks" "$backup_file"; then
      echo "Error: failed to prepare Codex hooks rollback file: $backup_file" >&2
      transaction_rc=1
    elif ! /bin/ln -s "$managed_hooks" "$replacement_link"; then
      echo "Error: failed to prepare managed Codex hooks symlink: $replacement_link" >&2
      transaction_rc=1
    elif ! _gsd_atomic_replace "$replacement_link" "$live_hooks"; then
      echo "Error: failed to atomically restore managed Codex hooks symlink." >&2
      transaction_rc=1
    else
      switched=1
      if [[ ! -L "$live_hooks" || "$(readlink "$live_hooks")" != "$managed_hooks" ]]; then
        echo "Error: restored Codex hooks symlink failed verification; rolling back." >&2
        transaction_rc=1
      elif ! trash "$backup_file"; then
        echo "Error: failed to preserve prior Codex hooks in Trash: $backup_file; rolling back." >&2
        transaction_rc=1
      else
        backup_file=""
      fi
    fi

    if (( transaction_rc != 0 && switched == 1 )); then
      if [[ -f "$backup_file" ]] && /bin/mv -f "$backup_file" "$live_hooks"; then
        backup_file=""
      else
        echo "Error: failed to roll back Codex hooks; backup remains at $backup_file" >&2
        rollback_rc=1
      fi
    fi
  } always {
    _gsd_trash_artifact "$replacement_link" || cleanup_rc=1
    if (( rollback_rc == 0 )); then
      _gsd_trash_artifact "$backup_file" || cleanup_rc=1
    fi
  }

  (( transaction_rc == 0 && rollback_rc == 0 && cleanup_rc == 0 ))
}

function _fix_claude_gsd_write_permissions() {
  local settings_file="${1:-$HOME/.claude/settings.json}"

  # GSD未インストール / 設定ファイル不在 → 何もせず正常終了
  [[ -f "$settings_file" ]] || return 0

  require_ai_setup_command jq || return 1

  local settings_dir="${settings_file:h}"
  local settings_name="${settings_file:t}"
  local tmp_out
  tmp_out="$(mktemp "$settings_dir/.${settings_name}.gsdfix.XXXXXX")" || return 1

  if ! jq '
    if (.permissions? | type) == "object"
       and (.permissions.allow? | type) == "array"
    then
      .permissions.allow |= (
        map(
          if . == "Write(.planning/*)" then "Edit(.planning/*)"
          elif . == "Write(STATE.md)" then "Edit(STATE.md)"
          else . end
        )
        | reduce .[] as $entry ([]; if index($entry) then . else . + [$entry] end)
      )
    else .
    end
  ' "$settings_file" > "$tmp_out"; then
    echo "Error: failed to rewrite GSD Write permissions in $settings_file." >&2
    _gsd_trash_artifact "$tmp_out" || true
    return 1
  fi

  # 変更が無ければ確認を出さずスキップ(既に修正済み / Write不在 / permissions不在)
  if json_files_semantically_equal "$settings_file" "$tmp_out"; then
    _gsd_trash_artifact "$tmp_out" || true
    return 0
  fi

  # 変更差分を表示してユーザー確認(他の設定を壊していないか目視できる)
  echo "GSDが追加した Write() permission を Edit() に修正します。変更差分:"
  show_json_diff "$tmp_out" "$settings_file" \
    "修正後 (proposed)" "現在の ~/.claude/settings.json"

  if ! confirm "この差分を ~/.claude/settings.json に適用しますか？" --default-no --no-cancel-msg; then
    echo "GSD permission 修正をスキップしました(settings.json は変更されません)。"
    _gsd_trash_artifact "$tmp_out" || true
    return 0
  fi

  # 承認された → アトミックに置換(同一ディレクトリのtmpからのmv)
  if ! _gsd_atomic_replace "$tmp_out" "$settings_file"; then
    echo "Error: failed to write updated Claude settings to $settings_file." >&2
    _gsd_trash_artifact "$tmp_out" || true
    return 1
  fi
}

function setup_gsd_core_for_runtime() {
  local runtime="$1"

  case "$runtime" in
    claude|codex) ;;
    *)
      echo "Error: expected GSD Core runtime to be claude or codex." >&2
      return 1
      ;;
  esac

  require_ai_setup_command npx || return 1
  require_ai_setup_command "$runtime" || return 1

  npx --yes @opengsd/gsd-core@latest "--${runtime}" --global --profile=standard --portable-hooks < /dev/null || return 1

  if [[ "$runtime" == "codex" ]]; then
    _restore_managed_codex_gsd_hooks || return 1
  elif [[ "$runtime" == "claude" ]]; then
    _fix_claude_gsd_write_permissions || return 1
  fi
}
