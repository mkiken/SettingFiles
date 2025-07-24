#!/bin/zsh

FILTER_TOOL='fzf-tmux'

if ! command -v ${FILTER_TOOL} > /dev/null 2>&1; then
  exit
fi

FILTER_COMMAND="${FILTER_TOOL} --cycle --exit-0 --ansi"
function filter(){
  ${=FILTER_COMMAND} $@
}

if [ -z "$FILTER_COMMAND" ]; then
  echo "FILTER_COMMAND variable is empty;"
  return;
fi

alias -g F='| filter'

# https://mogulla3.tech/articles/2021-09-06-search-command-history-with-incremental-search/
function select-history() {
  BUFFER=$(history -n -r 1 | awk '!seen[$0]++' | fzf --exact --reverse --no-sort --query="$LBUFFER" --cycle --prompt="History > ")
  CURSOR=${#BUFFER}
  # zle accept-line # 選択した履歴を即座に実行
}

# コマンドを履歴に残す
function save_history(){
  "$@" # 受け取った引数をそのままコマンドとして実行
  local ret=$? # コマンドの終了ステータスをキャプチャ
  if [[ $ret -ne 0 ]]; then
    return $ret # 元の終了ステータスを返す
  fi
  # 実行したコマンドを履歴に追加
  # -- は、以降の引数がオプションとして解釈されるのを防ぐ
  # (q-): Escaping of special characters, minimal quoting with single quotes
  print -s -- ${(q-)@}
}

alias fcd='fcd-down'
# fcd-down - cd to selected directory
# https://qiita.com/kamykn/items/aa9920f07487559c0c7e
function fcd-down() {
  local dir
  dir=$(fdad | filter --preview 'eza -T --color=always {} | head -100' +m) &&
  cd "$dir"
}

# 関数・エイリアス名をfzfで選んで実行するウィジェット
function falias() {
  local funcs aliases selected
  funcs=$(print -l ${(k)functions} \
    | grep -v "^_" \
    | grep -v "^-" \
    | grep -v "+" \
    | grep -v "\." \
    | grep -v "/" \
    | grep -v ":" \
    | grep -v "^falias")
  aliases=$(alias | cut -d'=' -f1)
  selected=$((echo "$funcs"; echo "$aliases") | sort | uniq | fzf --exact --reverse --no-sort --query="$LBUFFER" --cycle --prompt="関数/エイリアス > ")
  if [[ -z "$selected" ]]; then
    return $EXIT_CODE_SIGINT
  fi
    save_history "$selected" "$@"
}

alias fa='falias'