#!/bin/zsh

HERDR_CLAUDE_COMMAND="bash ~/.claude/hooks/herdr-agent-state.sh session"
HERDR_CODEX_COMMAND="bash ~/.codex/herdr-agent-state.sh session"

function _herdr_require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command not found: $1" >&2
    return 1
  fi
}

function setup_herdr_config() {
  local repo_root="${1:-$Repo}"
  local target_home="${2:-$HOME}"
  local source_config="${repo_root%/}/terminal/herdr/config.toml"
  local live_config="$target_home/.config/herdr/config.toml"
  local existing_target=""

  if [[ ! -f "$source_config" ]]; then
    echo "Error: managed Herdr config is unavailable: $source_config" >&2
    return 1
  fi

  if [[ -L "$live_config" ]]; then
    existing_target="$(readlink "$live_config")"
    if [[ "$existing_target" == "$source_config" ]]; then
      echo "✓ Already linked: $live_config -> $source_config"
      return 0
    fi
    echo "Error: Herdr config uses an unexpected symlink target: $existing_target" >&2
    return 1
  elif [[ -e "$live_config" ]]; then
    echo "Error: refusing to replace existing Herdr config: $live_config" >&2
    return 1
  fi

  mkdir -p "$(dirname "$live_config")" || return 1
  make_symlink "$source_config" "$live_config"
}

function _herdr_remove_managed_hook_commands() {
  local source_json="$1"
  local output_json="$2"

  jq '
    .hooks = ((.hooks // {})
      | with_entries(
          .value |= [
            .[]
            | .hooks = [
                (.hooks // [])[]
                | select(((.command // "") | contains("herdr-agent-state.sh")) | not)
              ]
            | select((.hooks | length) > 0)
          ]
        )
      | with_entries(select((.value | length) > 0)))
  ' "$source_json" >| "$output_json"
}

function _herdr_normalize_staged_hooks() {
  local runtime="$1"
  local staged_json="$2"
  local normalized_json="$3"
  local staged_hook="$4"
  local managed_command=""
  local staged_command=""

  case "$runtime" in
    claude) managed_command="$HERDR_CLAUDE_COMMAND" ;;
    codex) managed_command="$HERDR_CODEX_COMMAND" ;;
    *)
      echo "Error: expected Herdr integration runtime to be claude or codex." >&2
      return 1
      ;;
  esac

  staged_command="bash '$staged_hook' session"

  jq --sort-keys \
    --arg managed_command "$managed_command" \
    --arg staged_command "$staged_command" '
    walk(
      if type == "object"
        and ((.command? // null) | type) == "string"
        and .command == $staged_command
      then .command = $managed_command
      else .
      end
    )
  ' "$staged_json" >| "$normalized_json"
}

function _herdr_shared_state_snapshot() {
  local output_file="$1"
  local target_home="$2"
  local candidate=""
  local -a candidates=(
    "$target_home/.config/herdr/config.toml"
    "$target_home/.claude/settings.json"
    "$target_home/.claude/hooks/herdr-agent-state.sh"
    "$target_home/.codex/hooks.json"
    "$target_home/.codex/config.toml"
    "$target_home/.codex/herdr-agent-state.sh"
  )

  : >| "$output_file"
  for candidate in "${candidates[@]}"; do
    if [[ -L "$candidate" ]]; then
      if [[ -f "$candidate" ]]; then
        print -r -- \
          "link|$candidate|$(readlink "$candidate")|file|$(shasum -a 256 "$candidate" | /usr/bin/awk '{print $1}')" \
          >> "$output_file"
      else
        print -r -- "link|$candidate|$(readlink "$candidate")|non-file" >> "$output_file"
      fi
    elif [[ -f "$candidate" ]]; then
      print -r -- "file|$candidate|$(shasum -a 256 "$candidate" | /usr/bin/awk '{print $1}')" >> "$output_file"
    elif [[ -e "$candidate" ]]; then
      print -r -- "other|$candidate" >> "$output_file"
    else
      print -r -- "missing|$candidate" >> "$output_file"
    fi
  done
}

function _herdr_validate_staged_json() {
  local runtime="$1"
  local staged_json="$2"
  local managed_json="$3"
  local staging_root="$4"
  local normalized_json="$staging_root/${runtime}-normalized.json"
  local managed_sorted="$staging_root/${runtime}-managed.json"
  local staged_hook=""

  case "$runtime" in
    claude) staged_hook="$staging_root/claude/hooks/herdr-agent-state.sh" ;;
    codex) staged_hook="$staging_root/codex/herdr-agent-state.sh" ;;
    *)
      echo "Error: expected Herdr integration runtime to be claude or codex." >&2
      return 1
      ;;
  esac

  if ! _herdr_normalize_staged_hooks "$runtime" "$staged_json" "$normalized_json" "$staged_hook" \
    || ! jq --sort-keys . "$managed_json" >| "$managed_sorted"; then
    echo "Error: failed to normalize staged Herdr $runtime integration." >&2
    return 1
  fi

  if ! cmp -s "$normalized_json" "$managed_sorted"; then
    echo "Error: Herdr $runtime integration schema differs from the managed config." >&2
    diff -u "$managed_sorted" "$normalized_json" >&2 || true
    return 1
  fi
}

function _herdr_prepare_live_claude_registration() {
  local repo_root="$1"
  local target_home="$2"
  local staging_root="$3"
  local updated_json="$4"
  local managed_json="${repo_root%/}/ai/claude/settings.json"
  local live_json="$target_home/.claude/settings.json"
  local source_json="$live_json"
  local empty_json="$staging_root/claude-live-empty.json"
  local managed_entry="$staging_root/claude-managed-entry.json"

  if [[ -L "$live_json" ]]; then
    echo "Error: refusing to update symlinked Claude settings: $live_json" >&2
    return 1
  elif [[ ! -f "$live_json" ]]; then
    if [[ -e "$live_json" ]]; then
      echo "Error: Claude settings path is not a regular file: $live_json" >&2
      return 1
    fi
    print -r -- '{}' >| "$empty_json"
    source_json="$empty_json"
  fi

  if ! jq -e --arg command "$HERDR_CLAUDE_COMMAND" '
      [.hooks.SessionStart[]?
        | select([.hooks[]?.command] | index($command) != null)]
      | if length == 1 then .[0]
        else error("managed Claude Herdr registration must be unique")
        end
    ' "$managed_json" >| "$managed_entry"; then
    echo "Error: managed Claude Herdr hook registration is invalid: $managed_json" >&2
    return 1
  fi

  if ! jq --slurpfile managed_entry "$managed_entry" '
      .hooks = (.hooks // {})
      | .hooks.SessionStart = (
          [(.hooks.SessionStart // [])[]
            | .hooks = [
                (.hooks // [])[]
                | select(((.command // "") | contains("herdr-agent-state.sh")) | not)
              ]
            | select((.hooks | length) > 0)
          ] + [$managed_entry[0]]
        )
    ' "$source_json" >| "$updated_json"; then
    echo "Error: failed to update the live Claude Herdr hook registration." >&2
    return 1
  fi

}

function _herdr_live_config_ready() {
  local runtime="$1"
  local target_home="$2"
  local repo_root="$3"
  local managed_command=""
  local live_json=""
  local expected_target=""
  local existing_target=""

  case "$runtime" in
    claude)
      managed_command="$HERDR_CLAUDE_COMMAND"
      live_json="$target_home/.claude/settings.json"
      ;;
    codex)
      managed_command="$HERDR_CODEX_COMMAND"
      live_json="$target_home/.codex/hooks.json"
      expected_target="${repo_root%/}/ai/codex/hooks.json"
      if [[ ! -L "$live_json" ]]; then
        echo "Error: managed Codex hooks symlink is unavailable: $live_json" >&2
        return 1
      fi
      existing_target="$(readlink "$live_json")"
      if [[ "$existing_target" != "$expected_target" ]]; then
        echo "Error: Codex hooks use an unexpected symlink target: $existing_target" >&2
        return 1
      fi
      ;;
  esac

  if [[ ! -f "$live_json" ]] \
    || ! jq -e --arg command "$managed_command" \
      '[.hooks.SessionStart[]?.hooks[]?.command] | index($command) != null' \
      "$live_json" >/dev/null; then
    echo "Error: managed Herdr $runtime hook registration is not deployed: $live_json" >&2
    return 1
  fi
}

function _herdr_preflight_live_destination() {
  local destination="$1"
  local label="$2"
  local destination_dir="${destination:h}"

  if [[ -L "$destination_dir" ]]; then
    echo "Error: refusing Herdr $label destination directory symlink: $destination_dir" >&2
    return 1
  fi
  if [[ -e "$destination_dir" && ! -d "$destination_dir" ]]; then
    echo "Error: Herdr $label destination parent is not a directory: $destination_dir" >&2
    return 1
  fi
  if [[ ! -e "$destination_dir" && ! -d "${destination_dir:h}" ]]; then
    echo "Error: Herdr $label destination parent is unavailable: ${destination_dir:h}" >&2
    return 1
  fi
  if [[ -L "$destination" ]]; then
    echo "Error: refusing to replace symlinked Herdr $label destination: $destination" >&2
    return 1
  fi
  if [[ -e "$destination" && ! -f "$destination" ]]; then
    echo "Error: Herdr $label destination is not a regular file: $destination" >&2
    return 1
  fi
}

function _herdr_copy_deployment_file() {
  /bin/cp -p "$1" "$2"
}

function _herdr_prepare_settings_candidate() {
  local source_file="$1"
  local candidate="$2"
  local live_file="$3"
  local live_mode="600"

  /bin/chmod 600 "$candidate" || return 1
  /bin/cp "$source_file" "$candidate" || return 1
  if [[ -f "$live_file" ]]; then
    live_mode="$(/usr/bin/stat -f '%Lp' "$live_file")" || return 1
  fi
  /bin/chmod "$live_mode" "$candidate"
}

function _herdr_atomic_replace() {
  /bin/mv -f "$1" "$2"
}

function _herdr_deploy_live_files() {
  local staging_root="$1"
  local claude_settings_source="$2"
  local claude_settings_destination="$3"
  local claude_hook_source="$4"
  local claude_hook_destination="$5"
  local codex_hook_source="$6"
  local codex_hook_destination="$7"
  local deployment_artifacts="$staging_root/deployment-artifacts"
  local deployment_rc=0
  local rollback_rc=0
  local index=0
  local artifact_kind=""
  local artifact_path=""
  local destination_dir=""
  local destination_name=""
  local candidate_rc=0
  local -a sources=(
    "$claude_hook_source"
    "$codex_hook_source"
    "$claude_settings_source"
  )
  local -a destinations=(
    "$claude_hook_destination"
    "$codex_hook_destination"
    "$claude_settings_destination"
  )
  local -a labels=("Claude hook" "Codex hook" "Claude settings")
  local -a prepared=("" "" "")
  local -a backups=("" "" "")
  local -a existed=(0 0 0)
  local -a deployed=(0 0 0)
  local -a created_dirs=("" "" "")

  for index in 1 2 3; do
    if [[ ! -f "${sources[$index]}" ]]; then
      echo "Error: staged Herdr ${labels[$index]} was not generated: ${sources[$index]}" >&2
      return 1
    fi
    _herdr_preflight_live_destination "${destinations[$index]}" "${labels[$index]}" || return 1
  done

  mkdir -p "$deployment_artifacts" || return 1
  {
    for index in 1 2 3; do
      destination_dir="${destinations[$index]:h}"
      if [[ ! -d "$destination_dir" ]]; then
        if ! mkdir "$destination_dir"; then
          echo "Error: failed to create Herdr ${labels[$index]} destination directory." >&2
          deployment_rc=1
          break
        fi
        created_dirs[$index]="$destination_dir"
      fi
    done

    if (( deployment_rc == 0 )); then
      for index in 1 2 3; do
        destination_dir="${destinations[$index]:h}"
        destination_name="${destinations[$index]:t}"
        prepared[$index]="$(mktemp "$destination_dir/.${destination_name}.herdr-new.XXXXXX")" || {
          echo "Error: failed to create Herdr ${labels[$index]} deployment candidate." >&2
          deployment_rc=1
          break
        }
        if (( index == 3 )); then
          _herdr_prepare_settings_candidate \
            "${sources[$index]}" "${prepared[$index]}" "${destinations[$index]}"
        else
          _herdr_copy_deployment_file "${sources[$index]}" "${prepared[$index]}"
        fi
        candidate_rc=$?
        if (( candidate_rc != 0 )); then
          echo "Error: failed to prepare Herdr ${labels[$index]} deployment candidate." >&2
          deployment_rc=1
          break
        fi

        backups[$index]="$(mktemp "$destination_dir/.${destination_name}.herdr-backup.XXXXXX")" || {
          echo "Error: failed to create Herdr ${labels[$index]} rollback file." >&2
          deployment_rc=1
          break
        }
        if [[ -f "${destinations[$index]}" ]]; then
          existed[$index]=1
          if ! _herdr_copy_deployment_file "${destinations[$index]}" "${backups[$index]}"; then
            echo "Error: failed to preserve Herdr ${labels[$index]} before deployment." >&2
            deployment_rc=1
            break
          fi
        fi
      done
    fi

    if (( deployment_rc == 0 )); then
      for index in 1 2 3; do
        if ! _herdr_atomic_replace "${prepared[$index]}" "${destinations[$index]}"; then
          echo "Error: failed to deploy Herdr ${labels[$index]}; restoring prior live state." >&2
          deployment_rc=1
          break
        fi
        deployed[$index]=1
      done
    fi

    if (( deployment_rc != 0 )); then
      for index in 3 2 1; do
        (( deployed[$index] == 1 )) || continue
        if (( existed[$index] == 1 )); then
          if ! /bin/mv -f "${backups[$index]}" "${destinations[$index]}"; then
            echo "Error: failed to restore Herdr ${labels[$index]} after deployment failure." >&2
            rollback_rc=1
          fi
        elif ! /bin/mv -f "${destinations[$index]}" "${backups[$index]}"; then
          echo "Error: failed to remove newly deployed Herdr ${labels[$index]} during rollback." >&2
          rollback_rc=1
        fi
      done
    fi
  } always {
    for index in 1 2 3; do
      for artifact_kind in prepared backups; do
        if [[ "$artifact_kind" == "prepared" ]]; then
          artifact_path="${prepared[$index]}"
        else
          artifact_path="${backups[$index]}"
        fi
        if [[ -n "$artifact_path" && ( -e "$artifact_path" || -L "$artifact_path" ) ]]; then
          /bin/mv -f "$artifact_path" "$deployment_artifacts/${index}-${artifact_kind}" \
            || echo "Warning: failed to collect Herdr deployment artifact: $artifact_path" >&2
        fi
      done
    done
    if (( deployment_rc != 0 )); then
      for index in 3 2 1; do
        if [[ -n "${created_dirs[$index]}" && -d "${created_dirs[$index]}" ]]; then
          /bin/mv "${created_dirs[$index]}" "$deployment_artifacts/${index}-created-directory" \
            || echo "Warning: failed to collect Herdr deployment directory: ${created_dirs[$index]}" >&2
        fi
      done
    fi
  }

  (( rollback_rc == 0 )) || return 1
  return "$deployment_rc"
}

function _setup_herdr_integrations_in_staging() {
  local repo_root="$1"
  local target_home="$2"
  local staging_root="$3"
  local staged_home="$staging_root/home"
  local staged_claude="$staging_root/claude"
  local staged_codex="$staging_root/codex"
  local before_snapshot="$staging_root/shared-state-before"
  local after_snapshot="$staging_root/shared-state-after"
  local live_claude_settings="$target_home/.claude/settings.json"
  local live_claude_hook="$target_home/.claude/hooks/herdr-agent-state.sh"
  local live_codex_hook="$target_home/.codex/herdr-agent-state.sh"
  local prepared_claude_settings="$staging_root/claude-live-updated.json"
  local claude_source="${repo_root%/}/ai/claude/settings.json"
  local codex_hooks_source="${repo_root%/}/ai/codex/hooks.json"
  local codex_config_source="${repo_root%/}/ai/codex/config.toml"

  _herdr_live_config_ready codex "$target_home" "$repo_root" || return 1

  mkdir -p "$staged_home" "$staging_root/.config" "$staged_claude/hooks" "$staged_codex" || return 1
  _herdr_remove_managed_hook_commands "$claude_source" "$staged_claude/settings.json" || return 1
  _herdr_remove_managed_hook_commands "$codex_hooks_source" "$staged_codex/hooks.json" || return 1
  /bin/cp "$codex_config_source" "$staged_codex/config.toml" || return 1

  _herdr_shared_state_snapshot "$before_snapshot" "$target_home" || return 1

  HOME="$staged_home" XDG_CONFIG_HOME="$staging_root/.config" \
    CLAUDE_CONFIG_DIR="$staged_claude" CODEX_HOME="$staged_codex" \
    herdr integration install claude || return 1
  HOME="$staged_home" XDG_CONFIG_HOME="$staging_root/.config" \
    CLAUDE_CONFIG_DIR="$staged_claude" CODEX_HOME="$staged_codex" \
    herdr integration install codex || return 1

  _herdr_shared_state_snapshot "$after_snapshot" "$target_home" || return 1
  if ! cmp -s "$before_snapshot" "$after_snapshot"; then
    echo "Error: Herdr staging installer changed shared live state; refusing deployment." >&2
    diff -u "$before_snapshot" "$after_snapshot" >&2 || true
    return 1
  fi

  _herdr_validate_staged_json claude "$staged_claude/settings.json" "$claude_source" "$staging_root" || return 1
  _herdr_validate_staged_json codex "$staged_codex/hooks.json" "$codex_hooks_source" "$staging_root" || return 1
  if ! cmp -s "$staged_codex/config.toml" "$codex_config_source"; then
    echo "Error: Herdr changed the staged Codex config schema; refusing deployment." >&2
    diff -u "$codex_config_source" "$staged_codex/config.toml" >&2 || true
    return 1
  fi

  _herdr_prepare_live_claude_registration \
    "$repo_root" "$target_home" "$staging_root" "$prepared_claude_settings" || return 1
  if ! jq -e --arg command "$HERDR_CLAUDE_COMMAND" \
    '[.hooks.SessionStart[]?.hooks[]?.command] | index($command) != null' \
    "$prepared_claude_settings" >/dev/null; then
    echo "Error: prepared Claude settings omit the managed Herdr registration." >&2
    return 1
  fi

  _herdr_deploy_live_files \
    "$staging_root" \
    "$prepared_claude_settings" "$live_claude_settings" \
    "$staged_claude/hooks/herdr-agent-state.sh" "$live_claude_hook" \
    "$staged_codex/herdr-agent-state.sh" "$live_codex_hook" || return 1

  _herdr_live_config_ready claude "$target_home" "$repo_root" || return 1
}

function setup_herdr_integrations() {
  local repo_root="${1:-$Repo}"
  local target_home="${2:-$HOME}"
  local staging_root=""
  local setup_rc=0

  _herdr_require_command herdr || return 1
  _herdr_require_command jq || return 1
  _herdr_require_command shasum || return 1
  _herdr_require_command trash || return 1

  staging_root="$(mktemp -d "${TMPDIR:-/tmp}/settingfiles-herdr-integration.XXXXXX")" || return 1
  _setup_herdr_integrations_in_staging "$repo_root" "$target_home" "$staging_root"
  setup_rc=$?

  if [[ -n "$staging_root" && -d "$staging_root" ]]; then
    trash "$staging_root" || echo "Warning: failed to move Herdr staging directory to Trash: $staging_root" >&2
  fi
  return "$setup_rc"
}

function setup_herdr() {
  local repo_root="${1:-$Repo}"
  local target_home="${2:-$HOME}"

  setup_herdr_config "$repo_root" "$target_home" || return 1
  setup_herdr_integrations "$repo_root" "$target_home"
}
