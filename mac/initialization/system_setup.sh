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

echo 'System setup completed.'