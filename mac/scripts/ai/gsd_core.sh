#!/bin/zsh

function _normalize_codex_gsd_hooks() {
  local source_hooks="$1"
  local normalized_hooks="$2"
  local expected_home="${3:-$HOME}"

  jq --sort-keys --arg expected_home "$expected_home" '
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
  ' "$source_hooks" > "$normalized_hooks"
}

function _restore_managed_codex_gsd_hooks() {
  local repo_root="${1:-$Repo}"
  local gsd_home="${2:-$HOME}"
  local managed_hooks="${repo_root%/}/ai/codex/hooks.json"
  local live_hooks="$gsd_home/.codex/hooks.json"
  local live_target=""
  local live_is_managed_link=0
  local live_normalized=""
  local managed_normalized=""
  local comparison_rc=0
  local replacement_link="${live_hooks}.gsd-managed-link.$$"

  if [[ -z "$repo_root" || ! -f "$managed_hooks" ]]; then
    echo "Error: managed Codex hooks file is unavailable: $managed_hooks" >&2
    return 1
  fi

  if [[ -L "$live_hooks" ]]; then
    live_target="$(readlink "$live_hooks")"
    if [[ "$live_target" != "$managed_hooks" ]]; then
      echo "Error: Codex hooks use an unexpected symlink target: $live_target" >&2
      return 1
    fi
    live_is_managed_link=1
  elif [[ ! -f "$live_hooks" ]]; then
    echo "Error: GSD Core did not create Codex hooks: $live_hooks" >&2
    return 1
  fi

  require_ai_setup_command jq || return 1
  require_ai_setup_command trash || return 1

  live_normalized="$(mktemp -t gsd-codex-live-hooks)" || return 1
  managed_normalized="$(mktemp -t gsd-codex-managed-hooks)" || {
    /bin/rm -f "$live_normalized"
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
    /bin/rm -f "$live_normalized" "$managed_normalized"
  }

  (( comparison_rc == 0 )) || return 1

  if (( live_is_managed_link )); then
    return 0
  fi

  if [[ -e "$replacement_link" || -L "$replacement_link" ]]; then
    echo "Error: temporary Codex hooks link already exists: $replacement_link" >&2
    return 1
  fi

  /bin/ln -s "$managed_hooks" "$replacement_link" || return 1

  if ! trash "$live_hooks"; then
    /bin/rm -f "$replacement_link"
    return 1
  fi

  if ! /bin/mv "$replacement_link" "$live_hooks"; then
    echo "Error: generated Codex hooks were moved to Trash, but the managed replacement remains at $replacement_link." >&2
    return 1
  fi

  if [[ ! -L "$live_hooks" || "$(readlink "$live_hooks")" != "$managed_hooks" ]]; then
    echo "Error: failed to restore managed Codex hooks symlink." >&2
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
  fi
}
