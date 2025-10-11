#!/bin/zsh

FILTER_TOOL='fzf-tmux'

if ! command -v ${FILTER_TOOL} > /dev/null 2>&1; then
  exit
fi

FILTER_COMMAND="${FILTER_TOOL} --cycle --exit-0 --ansi"
function filter(){
  no_notify ${=FILTER_COMMAND} $@
}

if [ -z "$FILTER_COMMAND" ]; then
  echo "FILTER_COMMAND variable is empty;"
  return;
fi

alias -g F='| filter'

# https://mogulla3.tech/articles/2021-09-06-search-command-history-with-incremental-search/
function select-history() {
  BUFFER=$(history -n -r 1 | awk '!seen[$0]++' | filter --exact --reverse --no-sort --query="$LBUFFER" --cycle --prompt="History > ")
  CURSOR=${#BUFFER}
  # zle accept-line # 選択した履歴を即座に実行
}

# コマンドを履歴に残す
function save_history(){
  no_notify "$@" # 受け取った引数をそのままコマンドとして実行
  local ret=$? # コマンドの終了ステータスをキャプチャ

  # 成功時またはSIGINT/SIGPIPEの場合は履歴に保存
  if [[ $ret -eq 0 || $ret -eq $EXIT_CODE_SIGINT || $ret -eq $EXIT_CODE_SIGPIPE ]]; then
    # 実行したコマンドを履歴に追加
    # -- は、以降の引数がオプションとして解釈されるのを防ぐ
    # (q-): Escaping of special characters, minimal quoting with single quotes
    print -s -- ${(q-)@}
  fi

  # 元の終了ステータスを返す（0以外の場合も含む）
  return $ret
}

alias fcd='fcd-down'
# fcd-down - cd to selected directory
# https://qiita.com/kamykn/items/aa9920f07487559c0c7e
function fcd-down() {
  local dir
  dir=$(fdad | filter --preview 'eza -T --color=always {} | head -100' +m) &&
  cd "$dir"
}

# 関数・エイリアス名をfilterで選んでコマンドラインに挿入する
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
  selected=$((echo "$funcs"; echo "$aliases") | sort | uniq | filter --exact --reverse --no-sort --cycle --prompt="関数/エイリアス > ")
  if [[ -n "$selected" ]]; then
    print -z "$selected"
  fi
}

alias fa='falias'