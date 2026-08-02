#!/bin/zsh

function require_rtk_token_killer() {
  require_ai_setup_command rtk || return 1

  if ! rtk gain >/dev/null 2>&1; then
    echo "Error: rtk is not Rust Token Killer. Install rtk-ai/rtk." >&2
    return 1
  fi
}

function ensure_rtk_hook() {
  local settings_path="$1"
  local event_name="$2"
  local matcher="$3"
  local command="$4"
  local temp_path
  local -a jq_input

  require_ai_setup_command jq || return 1

  if [[ -e "$settings_path" ]] && ! jq empty "$settings_path" >/dev/null 2>&1; then
    echo "Error: Invalid JSON, refusing to modify: $settings_path" >&2
    return 1
  fi

  mkdir -p "${settings_path:h}" || return 1
  temp_path="$(mktemp "${settings_path}.XXXXXX")" || return 1
  if [[ -e "$settings_path" ]]; then
    jq_input=("$settings_path")
  else
    jq_input=(-n)
  fi

  if ! jq \
    --arg event_name "$event_name" \
    --arg matcher "$matcher" \
    --arg command "$command" \
    '
      def is_managed_rtk_hook:
        (.command? // "") as $hook_command
        | $hook_command == $command
          or ($hook_command | test("(^|/)rtk-(rewrite|gemini-hook)\\.sh$"));

      (. // {})
      | if type != "object"
        or (.hooks? != null and (.hooks | type != "object"))
        or (.hooks[$event_name]? != null and (.hooks[$event_name] | type != "array"))
      then error("unsupported hooks structure")
      else
        .hooks = (.hooks // {})
        | .hooks[$event_name] = (
            ((.hooks[$event_name] // [])
              | map(
                  .hooks = ((.hooks // []) | map(select(is_managed_rtk_hook | not)))
                  | select(.hooks | length > 0)
                )
            )
            + [{matcher: $matcher, hooks: [{type: "command", command: $command}]}]
          )
      end
    ' "${jq_input[@]}" > "$temp_path"; then
    trash "$temp_path"
    echo "Error: Failed to update RTK hook: $settings_path" >&2
    return 1
  fi

  /bin/mv "$temp_path" "$settings_path"
}
