#!/bin/zsh

# 関数定義を読み込み
source "$(dirname "$(dirname "$(dirname "$(realpath "${(%):-%x}")")")")/shell/zsh/alias/utils.zsh"

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "${(%):-%x}")")")")/"
Repo_shell="${Repo}shell/"

# sudo のパスワード待ちで気づけるよう、SUDO_PROMPT にベル(\a)と目立つ文言を仕込む。
# 環境変数なので brew bundle → cask インストーラ内部の sudo にも継承され、
# 実際に sudo が端末を掴んだ瞬間にベルが鳴る（NOPASSWD のような危険な回避はしない）。
function enable_sudo_bell() {
  export SUDO_PROMPT=$'\a🔔 [sudo] %p のパスワードを入力してください: '
}

function untap_stale_homebrew_taps() {
  local stale_taps=(
    "aku11i/tap"
    "dwarvesf/tap"
    "dwarvesf/homebrew-tap"
  )

  local stale_tap
  for stale_tap in "${stale_taps[@]}"; do
    if HOMEBREW_NO_AUTO_UPDATE=1 brew tap | /usr/bin/grep -Fxq "$stale_tap"; then
      HOMEBREW_NO_AUTO_UPDATE=1 brew untap "$stale_tap"
    fi
  done
}

function sync_enabled_vscode_extensions_to_brewfile() {
  local brewfile="${1:-${Repo}mac/Brewfile}"
  local state_db="${HOME}/Library/Application Support/Code/User/globalStorage/state.vscdb"

  if [[ ! -f "$brewfile" ]]; then
    echo "Warning: Brewfile not found, skipping VSCode extension sync: $brewfile" >&2
    return 0
  fi

  if ! command -v code >/dev/null 2>&1; then
    echo "Warning: code command not found, skipping VSCode extension sync." >&2
    return 0
  fi

  if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "Warning: sqlite3 command not found, skipping VSCode extension sync." >&2
    return 0
  fi

  if ! command -v node >/dev/null 2>&1; then
    echo "Warning: node command not found, skipping VSCode extension sync." >&2
    return 0
  fi

  if [[ ! -f "$state_db" ]]; then
    echo "Warning: VSCode state database not found, skipping VSCode extension sync: $state_db" >&2
    return 0
  fi

  local candidate installed_file disabled_file
  candidate="$(mktemp "${TMPDIR:-/tmp}/settingfiles_brewfile_vscode_candidate_XXXXXX")" || return 1
  installed_file="$(mktemp "${TMPDIR:-/tmp}/settingfiles_vscode_installed_XXXXXX")" || {
    /bin/rm -f "$candidate"
    return 1
  }
  disabled_file="$(mktemp "${TMPDIR:-/tmp}/settingfiles_vscode_disabled_XXXXXX")" || {
    /bin/rm -f "$candidate" "$installed_file"
    return 1
  }

  if ! /bin/cp -p "$brewfile" "$candidate"; then
    echo "Warning: failed to prepare VSCode extension sync candidate, skipping." >&2
    /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
    return 0
  fi

  if ! code --list-extensions >| "$installed_file"; then
    echo "Warning: failed to list VSCode extensions, skipping VSCode extension sync." >&2
    /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
    return 0
  fi

  if ! sqlite3 "$state_db" "select value from ItemTable where key in ('extensionsIdentifiers/disabled', 'vscode/extensionsIdentifiers/disabled');" >| "$disabled_file"; then
    echo "Warning: failed to read VSCode disabled extension state, skipping VSCode extension sync." >&2
    /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
    return 0
  fi

  local summary additions_count
  summary="$(
    node - "$brewfile" "$candidate" "$installed_file" "$disabled_file" <<'NODE'
const fs = require("fs");

const [brewfile, candidate, installedFile, disabledFile] = process.argv.slice(2);
const content = fs.readFileSync(brewfile, "utf8");

const normalize = (value) => String(value).trim().toLowerCase();
const unique = (values) => [...new Set(values.filter(Boolean))];

const installed = unique(
  fs.readFileSync(installedFile, "utf8")
    .split(/\r?\n/)
    .map(normalize)
);

const disabled = new Set();
for (const raw of fs.readFileSync(disabledFile, "utf8").split(/\r?\n/)) {
  if (!raw.trim()) continue;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      for (const item of parsed) {
        if (item && item.id) disabled.add(normalize(item.id));
      }
    }
  } catch {
    // Ignore unknown state rows; only the disabled extension JSON arrays matter.
  }
}

const hasFinalNewline = content.endsWith("\n");
const lines = hasFinalNewline ? content.slice(0, -1).split("\n") : content.split("\n");
const vscodePattern = /^vscode\s+"([^"]+)"/;
const existing = [];
const vscodeIndexes = [];

lines.forEach((line, index) => {
  const match = line.match(vscodePattern);
  if (!match) return;
  existing.push(match[1]);
  vscodeIndexes.push(index);
});

const existingLower = new Set(existing.map(normalize));
const additions = installed
  .filter((id) => !disabled.has(id) && !existingLower.has(id))
  .sort((a, b) => a.localeCompare(b));

let outputLines = lines;
if (additions.length > 0) {
  const vscodeLines = [...existing, ...additions]
    .sort((a, b) => normalize(a).localeCompare(normalize(b)))
    .map((id) => `vscode "${id}"`);

  if (vscodeIndexes.length > 0) {
    const firstVscodeIndex = vscodeIndexes[0];
    outputLines = [];
    lines.forEach((line, index) => {
      if (index === firstVscodeIndex) outputLines.push(...vscodeLines);
      if (!vscodePattern.test(line)) outputLines.push(line);
    });
  } else {
    const masIndex = lines.findIndex((line) => /^mas\s+"/.test(line));
    const insertIndex = masIndex === -1 ? lines.length : masIndex;
    outputLines = [...lines];
    outputLines.splice(insertIndex, 0, ...vscodeLines, "");
  }
}

fs.writeFileSync(candidate, outputLines.join("\n") + (hasFinalNewline ? "\n" : ""));

console.log(`Installed VSCode extensions: ${installed.length}`);
console.log(`Globally disabled VSCode extensions: ${[...disabled].sort().join(", ") || "none"}`);
console.log(`ADDED_COUNT=${additions.length}`);
if (additions.length > 0) {
  console.log("Additions:");
  for (const id of additions) console.log(`  ${id}`);
}
NODE
  )" || {
    echo "Warning: failed to build VSCode extension sync candidate, skipping." >&2
    /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
    return 0
  }

  print -r -- "$summary"
  additions_count="$(print -r -- "$summary" | /usr/bin/awk -F= '$1 == "ADDED_COUNT" { print $2; exit }')"

  if [[ -z "$additions_count" || "$additions_count" -eq 0 ]]; then
    echo "✓ Brewfile already contains all enabled VSCode extensions."
    /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
    return 0
  fi

  local review_signature=""
  local last_reviewed_at=""
  local repeated_action=""
  local candidate_label="VSCode extension sync candidate for $brewfile"

  review_signature=$(_diff_review_file_signature "vscode_extension_sync" "$candidate" "$brewfile" "$candidate_label" "$brewfile" 2>/dev/null || true)
  if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
    last_reviewed_at=$(_diff_review_last_reviewed_at "$review_signature" 2>/dev/null || true)
    if [[ -n "$last_reviewed_at" ]]; then
      repeated_action=$(_diff_review_prompt_repeated_copy "$review_signature" "$last_reviewed_at" "VSCode extension Brewfile sync action required: $brewfile")
      case "$repeated_action" in
        overwrite)
          echo "/bin/cp \"$candidate\" \"$brewfile\""
          /bin/cp "$candidate" "$brewfile"
          /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
          return $?
          ;;
        skip)
          echo "Skipped: $brewfile"
          /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
          return 0
          ;;
        view)
          ;;
      esac
    fi
  fi

  echo ""
  echo "=== VSCode extensions Brewfile sync candidate ==="
  show_file_diff "$candidate" "$brewfile" "$candidate_label" "$brewfile"
  echo "================================================="

  if [[ -n "$review_signature" ]] && ! _diff_review_smart_merge_auto_enabled; then
    _diff_review_record "$review_signature"
  fi

  if confirm "VSCodeの有効拡張同期候補で ${brewfile} を上書きしますか？" --default-no --no-cancel-msg; then
    echo "/bin/cp \"$candidate\" \"$brewfile\""
    /bin/cp "$candidate" "$brewfile"
  else
    echo "Skipped: $brewfile"
  fi

  /bin/rm -f "$candidate" "$installed_file" "$disabled_file"
}

# herdr の公式 SKILL.md (AI がherdrのCLIを操作するためのスキル)を upstream から取り込む。
# 差分があれば repo 内ファイルを上書きするが git add はしない — コミット判断は
# 人間が `git diff` でレビューしてから行う。取得失敗時は既存ファイルを保護し、
# update 全体を止めないよう常に rc=0 で返す(best-effort)。
function sync_herdr_skill() {
  local repo_root="${1:-$Repo}"
  local skill_path="${repo_root%/}/ai/common/skills/herdr/SKILL.md"
  local upstream_url="https://raw.githubusercontent.com/ogulcancelik/herdr/master/SKILL.md"
  local tmp_file

  if ! command -v curl >/dev/null 2>&1; then
    echo "Warning: herdr skill sync skipped — curl not found" >&2
    return 0
  fi

  if [[ ! -f "$skill_path" ]]; then
    echo "Warning: herdr skill sync skipped — managed skill file is missing: $skill_path" >&2
    return 0
  fi

  tmp_file="$(mktemp "${TMPDIR:-/tmp}/herdr-skill-sync.XXXXXX")" || {
    echo "Warning: herdr skill sync skipped — failed to create temp file" >&2
    return 0
  }

  # コマンド置換 $(...) は末尾改行を剥がしてしまうため、curl の出力は直接
  # ファイルへリダイレクトして末尾改行を含めた完全な内容を保持する。
  # 改行のみの応答も実質空とみなし、-s (サイズ0判定) ではなく中身の有無で判定する。
  if ! curl -fsSL "$upstream_url" >"$tmp_file" 2>/dev/null || [[ -z "$(<"$tmp_file")" ]]; then
    echo "Warning: herdr skill sync skipped — failed to fetch $upstream_url" >&2
    /bin/rm -f "$tmp_file"
    return 0
  fi

  if cmp -s "$tmp_file" "$skill_path"; then
    echo "herdr skill: up to date"
    /bin/rm -f "$tmp_file"
    return 0
  fi

  /bin/cp "$tmp_file" "$skill_path"
  /bin/rm -f "$tmp_file"
  echo "herdr skill UPDATED from upstream — review with 'git diff' before committing: $skill_path"
  return 0
}

# genshijin の常時有効化ルールを upstream から同期する。差分は作業ツリーに残し、
# 取得失敗時は既存の検証済みルールを維持して update を継続する。
function sync_genshijin_rule() {
  local repo_root="${1:-$Repo}"
  local rule_path="${repo_root%/}/ai/common/genshijin-activate.md"
  local upstream_url="https://raw.githubusercontent.com/InterfaceX-co-jp/genshijin/main/rules/genshijin-activate.md"
  local tmp_file

  if ! command -v curl >/dev/null 2>&1; then
    echo "Warning: genshijin rule sync skipped — curl not found" >&2
    return 0
  fi

  if [[ ! -f "$rule_path" ]]; then
    echo "Warning: genshijin rule sync skipped — managed rule file is missing: $rule_path" >&2
    return 0
  fi

  tmp_file="$(mktemp "${TMPDIR:-/tmp}/genshijin-rule-sync.XXXXXX")" || {
    echo "Warning: genshijin rule sync skipped — failed to create temp file" >&2
    return 0
  }

  if ! curl -fsSL "$upstream_url" >"$tmp_file" 2>/dev/null || [[ -z "$(<"$tmp_file")" ]]; then
    echo "Warning: genshijin rule sync skipped — failed to fetch $upstream_url" >&2
    /bin/rm -f "$tmp_file"
    return 0
  fi

  if ! /usr/bin/grep -Fq "原始人のように簡潔に返答せよ" "$tmp_file"; then
    echo "Warning: genshijin rule sync skipped — upstream content was unexpected" >&2
    /bin/rm -f "$tmp_file"
    return 0
  fi

  if cmp -s "$tmp_file" "$rule_path"; then
    echo "genshijin rule: up to date"
    /bin/rm -f "$tmp_file"
    return 0
  fi

  /bin/cp "$tmp_file" "$rule_path"
  /bin/rm -f "$tmp_file"
  echo "genshijin rule UPDATED from upstream — review with 'git diff' before committing: $rule_path"
  return 0
}

function setup_ai_skills() {
  local dest_dir="$1"
  shift

  mkdir -p "$dest_dir"

  local skills_root skill_dir skill_name
  for skills_root in "$@"; do
    if [[ ! -d "$skills_root" ]]; then
      continue
    fi

    for skill_dir in "${skills_root}"/*(-/N); do
      skill_name=$(basename "$skill_dir")
      make_symlink "$skill_dir" "${dest_dir}/${skill_name}"
    done
  done
}

function setup_ai_pr_tools() {
  local source_dir="${Repo}shell/common/pr"
  local dest_bin="$HOME/.config/ai-pr/bin"
  local file

  if [[ -d "$dest_bin" && ! -L "$dest_bin" ]]; then
    for file in "${source_dir}"/*.sh(N) "${source_dir}"/*.py(N); do
      if [[ -f "$file" ]]; then
        make_symlink "$file" "${dest_bin}/$(basename "$file")"
      fi
    done
    return
  fi

  make_symlink "$source_dir" "$dest_bin"
}

# Codex の共通プロンプト、genshijin ルール、ローカル設定を _AGENTS.md に連結する
function generate_codex_agents() {
  { /bin/cat "${Repo}ai/common/prompt_base.md"; echo; /bin/cat "${Repo}ai/common/genshijin-activate.md"; echo; /bin/cat "${Repo}ai/common/genshijin-file-policy.md"; echo; /bin/cat "${Repo}ai/codex/codex_base.md"; } > "${Repo}ai/codex/_AGENTS.md"
}

# pr-review-subagents のレビュアー定義を共有フラグメントから生成する
# 生成物: ai/claude/agents/pr-reviewer-*.md, ai/gemini/agents/pr-reviewer-*.md, ai/codex/agents/pr_reviewer_*.toml
# 編集は ai/common/pr_review_subagents/ と ai/<platform>/agents_src/ へ（生成物は編集しない）
function generate_pr_reviewer_agents() {
  local platform="$1"
  local common="${Repo}ai/common/pr_review_subagents"
  local src="${Repo}ai/${platform}/agents_src"
  local notice="GENERATED FILE - do not edit. Sources: ai/common/pr_review_subagents/, ai/${platform}/agents_src/. Regen: mac/updates/${platform}.sh."
  local dim out

  for dim in bugs security design history tests performance claims; do
    case "$platform" in
      claude | gemini)
        out="${Repo}ai/${platform}/agents/pr-reviewer-${dim}.md"
        {
          # 実行時トークンを消費しないよう、注釈は本文ではなく frontmatter 内の YAML コメントに埋め込む
          awk -v notice="$notice" 'NR > 1 && /^---$/ && !done { print "# " notice; done = 1 } { print }' "${src}/head_${dim}.md"
          echo
          /bin/cat "${common}/intro_${dim}.md"
          echo
          /bin/cat "${src}/rules_${dim}.md"
          /bin/cat "${src}/rules_common.md"
          echo
          /bin/cat "${common}/format_${dim}.md"
        } > "$out"
        ;;
      codex)
        out="${Repo}ai/codex/agents/pr_reviewer_${dim}.toml"
        # 本文は TOML の ''' リテラル文字列に埋め込むため、フラグメントに ''' が混入したら生成を失敗させる
        if /usr/bin/grep -q "'''" "${common}/intro_${dim}.md" "${common}/format_${dim}.md" "${src}/rules_${dim}.md" "${src}/rules_common.md"; then
          echo "Error: ''' found in pr_reviewer_${dim} fragments; it would break the TOML literal string." >&2
          return 1
        fi
        {
          printf '# %s\n' "$notice"
          /bin/cat "${src}/head_${dim}.toml"
          /bin/cat "${common}/intro_${dim}.md"
          echo
          /bin/cat "${src}/rules_${dim}.md"
          /bin/cat "${src}/rules_common.md"
          echo
          /bin/cat "${common}/format_${dim}.md"
          printf "'''\n"
        } > "$out"
        ;;
      *)
        echo "Error: unknown platform '${platform}' for generate_pr_reviewer_agents." >&2
        return 1
        ;;
    esac
  done
}

# pr-review-subagents の敵対的検証エージェント定義を共有フラグメントから生成する
# 生成物: ai/claude/agents/pr-review-verifier.md, ai/gemini/agents/pr-review-verifier.md, ai/codex/agents/pr_review_verifier.toml
# 編集は ai/common/pr_review_subagents/verifier_core.md と ai/<platform>/agents_src/pr_review_verify/ へ（生成物は編集しない）
function generate_pr_review_verifier_agents() {
  local platform="$1"
  local core="${Repo}ai/common/pr_review_subagents/verifier_core.md"
  local src="${Repo}ai/${platform}/agents_src/pr_review_verify"
  local notice="GENERATED FILE - do not edit. Sources: ai/common/pr_review_subagents/verifier_core.md, ai/${platform}/agents_src/pr_review_verify/. Regen: mac/updates/${platform}.sh."
  local out

  case "$platform" in
    claude | gemini)
      out="${Repo}ai/${platform}/agents/pr-review-verifier.md"
      {
        # 実行時トークンを消費しないよう、注釈は本文ではなく frontmatter 内の YAML コメントに埋め込む
        awk -v notice="$notice" 'NR > 1 && /^---$/ && !done { print "# " notice; done = 1 } { print }' "${src}/head_verifier.md"
        echo
        /bin/cat "$core"
      } > "$out"
      ;;
    codex)
      out="${Repo}ai/codex/agents/pr_review_verifier.toml"
      # 本文は TOML の ''' リテラル文字列に埋め込むため、フラグメントに ''' が混入したら生成を失敗させる
      if /usr/bin/grep -q "'''" "$core"; then
        echo "Error: ''' found in pr_review_verifier fragment; it would break the TOML literal string." >&2
        return 1
      fi
      {
        printf '# %s\n' "$notice"
        /bin/cat "${src}/head_verifier.toml"
        /bin/cat "$core"
        printf "'''\n"
      } > "$out"
      ;;
    *)
      echo "Error: unknown platform '${platform}' for generate_pr_review_verifier_agents." >&2
      return 1
      ;;
  esac
}

# config-audit の監査エージェント定義を共有フラグメントから生成する
# 生成物: ai/claude/agents/config-auditor-*.md, ai/gemini/agents/config-auditor-*.md, ai/codex/agents/config_auditor_*.toml
# 編集は ai/common/config_audit_subagents/ と ai/<platform>/agents_src/config_audit/ へ（生成物は編集しない）
function generate_config_auditor_agents() {
  local platform="$1"
  local common="${Repo}ai/common/config_audit_subagents"
  local src="${Repo}ai/${platform}/agents_src/config_audit"
  local notice="GENERATED FILE - do not edit. Sources: ai/common/config_audit_subagents/, ai/${platform}/agents_src/config_audit/. Regen: mac/updates/${platform}.sh."
  local dim out

  for dim in default conflict overlap patch ambiguity concise; do
    case "$platform" in
      claude | gemini)
        out="${Repo}ai/${platform}/agents/config-auditor-${dim}.md"
        {
          # 実行時トークンを消費しないよう、注釈は本文ではなく frontmatter 内の YAML コメントに埋め込む
          awk -v notice="$notice" 'NR > 1 && /^---$/ && !done { print "# " notice; done = 1 } { print }' "${src}/head_${dim}.md"
          echo
          /bin/cat "${common}/intro_${dim}.md"
          echo
          /bin/cat "${common}/rules_common.md"
          echo
          /bin/cat "${common}/format_${dim}.md"
        } > "$out"
        ;;
      codex)
        out="${Repo}ai/codex/agents/config_auditor_${dim}.toml"
        # 本文は TOML の ''' リテラル文字列に埋め込むため、フラグメントに ''' が混入したら生成を失敗させる
        if /usr/bin/grep -q "'''" "${common}/intro_${dim}.md" "${common}/rules_common.md" "${common}/format_${dim}.md"; then
          echo "Error: ''' found in config_auditor_${dim} fragments; it would break the TOML literal string." >&2
          return 1
        fi
        {
          printf '# %s\n' "$notice"
          /bin/cat "${src}/head_${dim}.toml"
          /bin/cat "${common}/intro_${dim}.md"
          echo
          /bin/cat "${common}/rules_common.md"
          echo
          /bin/cat "${common}/format_${dim}.md"
          printf "'''\n"
        } > "$out"
        ;;
      *)
        echo "Error: unknown platform '${platform}' for generate_config_auditor_agents." >&2
        return 1
        ;;
    esac
  done
}

# review-fix の設計/実装サブエージェント定義を共有フラグメントから生成する（Codex のみ; Claude はサブエージェント自身が実行時にロールコアを読む）
# 生成物: ai/codex/agents/review_fix_{designer,implementer}.toml
# 編集は ai/common/review_fix_subagents/ と ai/codex/agents_src/review_fix/ へ（生成物は編集しない）
function generate_review_fix_agents() {
  local common="${Repo}ai/common/review_fix_subagents"
  local src="${Repo}ai/codex/agents_src/review_fix"
  local notice="GENERATED FILE - do not edit. Sources: ai/common/review_fix_subagents/, ai/codex/agents_src/review_fix/. Regen: mac/updates/codex.sh."
  local role out

  for role in designer implementer; do
    out="${Repo}ai/codex/agents/review_fix_${role}.toml"
    # 本文は TOML の ''' リテラル文字列に埋め込むため、フラグメントに ''' が混入したら生成を失敗させる
    if /usr/bin/grep -q "'''" "${common}/${role}_core.md"; then
      echo "Error: ''' found in review_fix_${role} fragment; it would break the TOML literal string." >&2
      return 1
    fi
    {
      printf '# %s\n' "$notice"
      /bin/cat "${src}/head_${role}.toml"
      /bin/cat "${common}/${role}_core.md"
      printf "'''\n"
    } > "$out"
  done
}

# 共有コアスキルの SKILL.md を skill_head.md + ai/common のコア群 (+ skill_tail.md があれば) の連結で生成する
# 引数: <skillsディレクトリ> <entries...>  entry形式: <skill名>:<ai/common からのコア相対パス（スペース区切りで複数可、記載順に連結）>
# 生成物: <skillsディレクトリ>/<skill名>/SKILL.md（編集はソースへ、生成物は編集しない）
function generate_core_skills() {
  local skills_dir="$1"
  shift
  local entry skill_dir core

  for entry in "$@"; do
    skill_dir="${skills_dir}/${entry%%:*}"
    {
      /bin/cat "${skill_dir}/skill_head.md"
      for core in ${(s: :)${entry#*:}}; do
        echo
        /bin/cat "${Repo}ai/common/${core}"
      done
      if [[ -f "${skill_dir}/skill_tail.md" ]]; then
        echo
        /bin/cat "${skill_dir}/skill_tail.md"
      fi
    } > "${skill_dir}/SKILL.md"
  done
}

# 単一の真実源: generated shared-core スキルの <skill名>:<コアパス> エントリ一覧。
# generate_codex_skills / generate_gemini_skills / verify_ai_skill_generation_idempotency が
# 全てここから読む。新規スキルを shared-core 化するときはこの2配列に追記するだけでよく、
# 生成物パスの列挙（旧 verify_ai_skill_generation_idempotency のハードコード配列）は不要。
CODEX_CORE_SKILL_ENTRIES=(
  "pr-review:pr_review_core.md pr_review_finding_format.md"
  "pr-comment-review:pr_comment_review_core.md"
  "pr-comment-implement:pr_comment_implement_core.md"
  "pr-body:pr_body_core.md pr_body_format.md"
  "pr-comment-post:pr_comment_post_core.md pr_post_mechanics_core.md"
  "pr-create-by-branch:pr_create_by_branch_core.md pr_body_format.md"
  "pr-review-subagents:pr_review_subagents/orchestrator_core.md pr_review_finding_format.md"
  "config-audit:config_audit_subagents/orchestrator_core.md"
  "review-merge:review_merge_core.md"
  "review-post:review_post_core.md pr_post_mechanics_core.md"
  "review-fix:review_fix_core.md"
)

GEMINI_CORE_SKILL_ENTRIES=(
  "fact-based:fact_based_core.md"
  "write-tests:write_tests_core.md"
)

function generate_codex_skills() {
  generate_core_skills "${Repo}ai/codex/skills" "${CODEX_CORE_SKILL_ENTRIES[@]}"
}

function generate_gemini_skills() {
  generate_core_skills "${Repo}ai/gemini/skills" "${GEMINI_CORE_SKILL_ENTRIES[@]}"
}

function generate_ai_skills() {
  generate_codex_skills && generate_gemini_skills
}

# generator を2回実行し、指定された生成物の SHA-256 が変化しないことを検証する。
# 引数: <generator関数名> <生成物パス...>
function verify_generator_idempotency() {
  local generator_name="${1:-}"
  shift 2>/dev/null || true

  if [[ -z "$generator_name" || "$#" -eq 0 ]]; then
    echo "Error: usage: verify_generator_idempotency <generator-function> <output-path...>" >&2
    return 2
  fi
  if ! typeset -f "$generator_name" >/dev/null; then
    echo "Error: generator function not found: $generator_name" >&2
    return 2
  fi

  local output_count="$#"
  local generated_file hash_line file_hash exit_code
  local mismatch_count=0
  typeset -A before_hashes

  "$generator_name"
  exit_code=$?
  if (( exit_code != 0 )); then
    echo "Error: generator failed on first pass: $generator_name" >&2
    return "$exit_code"
  fi

  for generated_file in "$@"; do
    if [[ ! -f "$generated_file" ]]; then
      echo "Error: generated output not found after first pass: $generated_file" >&2
      return 1
    fi
    hash_line="$(shasum -a 256 "$generated_file")"
    exit_code=$?
    if (( exit_code != 0 )); then
      echo "Error: failed to hash generated output: $generated_file" >&2
      return "$exit_code"
    fi
    if [[ -z "$hash_line" ]]; then
      echo "Error: failed to hash generated output: $generated_file" >&2
      return 1
    fi
    file_hash="${hash_line%% *}"
    before_hashes[$generated_file]="$file_hash"
  done

  "$generator_name"
  exit_code=$?
  if (( exit_code != 0 )); then
    echo "Error: generator failed on second pass: $generator_name" >&2
    return "$exit_code"
  fi

  for generated_file in "$@"; do
    if [[ ! -f "$generated_file" ]]; then
      echo "Error: generated output not found after second pass: $generated_file" >&2
      return 1
    fi
    hash_line="$(shasum -a 256 "$generated_file")"
    exit_code=$?
    if (( exit_code != 0 )); then
      echo "Error: failed to hash generated output: $generated_file" >&2
      return "$exit_code"
    fi
    if [[ -z "$hash_line" ]]; then
      echo "Error: failed to hash generated output: $generated_file" >&2
      return 1
    fi
    file_hash="${hash_line%% *}"
    if [[ "${before_hashes[$generated_file]}" != "$file_hash" ]]; then
      echo "Error: generated output changed on second pass: $generated_file" >&2
      mismatch_count=$((mismatch_count + 1))
    fi
  done

  if (( mismatch_count != 0 )); then
    return 1
  fi
  echo "Verified idempotent generation for ${output_count} output(s)."
}

function verify_ai_skill_generation_idempotency() {
  local generated_files=()
  local entry

  for entry in "${CODEX_CORE_SKILL_ENTRIES[@]}"; do
    generated_files+=("${Repo}ai/codex/skills/${entry%%:*}/SKILL.md")
  done
  for entry in "${GEMINI_CORE_SKILL_ENTRIES[@]}"; do
    generated_files+=("${Repo}ai/gemini/skills/${entry%%:*}/SKILL.md")
  done

  verify_generator_idempotency generate_ai_skills "${generated_files[@]}"
}

function verify_review_fix_agent_generation_idempotency() {
  verify_generator_idempotency generate_review_fix_agents \
    "${Repo}ai/codex/agents/review_fix_designer.toml" \
    "${Repo}ai/codex/agents/review_fix_implementer.toml"
}

# 全プラットフォームの敵対的検証エージェントを一括生成する（冪等性検証用ラッパー）
function generate_pr_review_verifier_agents_all() {
  local platform
  for platform in claude gemini codex; do
    generate_pr_review_verifier_agents "$platform" || return 1
  done
}

function verify_pr_review_verifier_agent_generation_idempotency() {
  verify_generator_idempotency generate_pr_review_verifier_agents_all \
    "${Repo}ai/claude/agents/pr-review-verifier.md" \
    "${Repo}ai/gemini/agents/pr-review-verifier.md" \
    "${Repo}ai/codex/agents/pr_review_verifier.toml"
}

function require_ai_setup_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: $command_name is not installed or not on PATH." >&2
    return 1
  fi
}

function require_context_mode_node() {
  require_ai_setup_command node || return 1
  require_ai_setup_command npm || return 1

  node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 5)) {
  console.error(`Error: context-mode requires Node.js >= 22.5.0. Found ${process.versions.node}.`);
  process.exit(1);
}
'
}

function setup_context_mode_cli() {
  if [[ "${CONTEXT_MODE_CLI_SETUP_DONE:-}" == "1" ]]; then
    echo "✓ context-mode CLI already handled for this run."
    return 0
  fi

  echo "Ensuring context-mode CLI..."

  require_context_mode_node || return 1

  npm install -g context-mode@latest || return 1

  export CONTEXT_MODE_CLI_SETUP_DONE=1
}
