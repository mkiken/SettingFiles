#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Shell setting
# ログインシェルの設定（自分のシェル変更は sudo 不要）
# 既に何らかの zsh がログインシェルなら何もしない（初回のみ実行）
# ※ current_shell と target_shell を単純に文字列比較すると、
#   system標準 (/bin/zsh) と Homebrew版 (/usr/local/bin/zsh 等) が別パスとして扱われ、
#   既に zsh 運用中でも不要な chsh が走ってしまうため、basename で「zshかどうか」だけを見る
current_shell="$(dscl . -read "/Users/$USER" UserShell 2>/dev/null | awk '{print $2}')"
target_shell="$(command -v zsh)"   # 環境依存の zsh パスを動的解決（/bin/zsh とは限らない）

if [[ -z "$target_shell" ]]; then
  echo "zsh が見つからないためログインシェル変更をスキップ" >&2
elif [[ "$(basename "$current_shell" 2>/dev/null)" == "zsh" ]]; then
  echo "ログインシェルは既に zsh (${current_shell}) です。スキップします。"
else
  # /etc/shells に無いパスは chsh が拒否するため、必要なら追記を案内（自動で sudo は増やさない）
  if ! /usr/bin/grep -Fxq "$target_shell" /etc/shells 2>/dev/null; then
    echo "注意: ${target_shell} が /etc/shells に未登録です。必要なら登録してください:" >&2
    echo "  echo '${target_shell}' | sudo tee -a /etc/shells" >&2
  fi
  chsh -s "$target_shell"
fi

# Touch ID で sudo を承認できるようにする。/etc/pam.d/sudo_local は OS アップデート後も保持される公式の拡張ポイント。
# sudo プロンプトが画面中央のダイアログになるため、長時間スクリプト途中のパスワード要求にも気づける。
# tmux 内でも Touch ID を使えるようにする pam_reattach.so（Homebrew の pam-reattach）は必ず pam_tid.so より前の行に置く。
function setup_touchid_sudo() {
  local sudo_local="/etc/pam.d/sudo_local"
  local reattach_module="$(brew --prefix 2>/dev/null)/lib/pam/pam_reattach.so"

  # sudo_local 非対応の古い macOS（Sonoma 未満）ではテンプレートが無いためスキップ
  if [[ ! -f "${sudo_local}.template" ]]; then
    echo "注意: ${sudo_local}.template が無いため Touch ID sudo 設定をスキップします。" >&2
    return 0
  fi

  if [[ -f "$sudo_local" ]]; then
    if /usr/bin/grep -q "pam_tid.so" "$sudo_local"; then
      echo "✓ Touch ID sudo は設定済みです (${sudo_local})。"
    else
      # 想定外の既存内容は上書きせず、報告して手動対応を促す（make_symlink と同じ方針）
      echo "注意: ${sudo_local} が既に存在しますが pam_tid.so が含まれていません。必要なら手動で追記してください:" >&2
      echo "  auth       optional       ${reattach_module}" >&2
      echo "  auth       sufficient     pam_tid.so" >&2
    fi
    return 0
  fi

  local content="auth       sufficient     pam_tid.so"
  if [[ -f "$reattach_module" ]]; then
    content="auth       optional       ${reattach_module}"$'\n'"${content}"
  else
    echo "注意: pam_reattach.so が見つかりません。tmux 内では Touch ID が効きません（brew bundle 後に再実行してください）。" >&2
  fi

  if print -r -- "$content" | sudo /usr/bin/tee "$sudo_local" >/dev/null; then
    echo "✓ Touch ID sudo を設定しました (${sudo_local})。"
  else
    echo "Warning: ${sudo_local} の作成に失敗しました。" >&2
  fi
}

setup_touchid_sudo

echo 'System setup completed.'