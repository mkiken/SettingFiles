#!/bin/zsh

FILTER_TOOL='fzf-tmux'

if ! command -v ${FILTER_TOOL} > /dev/null 2>&1; then
  exit
fi

FILTER_COMMAND="${FILTER_TOOL} --cycle --exit-0 --ansi"

# フィルターツール (fzf-tmux) のラッパー関数
# 引数: fzf-tmuxに渡すオプション (例: --preview, --query など)
# 戻り値: 選択された項目
function filter(){
  no_notify ${=FILTER_COMMAND} $@
}

alias -g F='| filter'

# コマンド履歴をインクリメンタル検索で選択する関数
# 重複する履歴を除外し、現在のバッファ内容を初期クエリとして使用
# 選択した履歴をコマンドラインバッファに設定 (Enterで実行)
# 引数: なし
# 環境変数: FILTER_HISTORY_LIMIT - 検索対象の履歴件数 (デフォルト: 5000)
# 参考: https://mogulla3.tech/articles/2021-09-06-search-command-history-with-incremental-search/
function select-history() {
  local max_history=${FILTER_HISTORY_LIMIT:-5000}
  BUFFER=$(history -n -r -${max_history} | awk '!seen[$0]++' | filter --exact --reverse --no-sort --query="$LBUFFER" --cycle --prompt="History > ")
  CURSOR=${#BUFFER}
  # zle accept-line # 選択した履歴を即座に実行
}

# コマンドを実行し、成功時またはシグナル終了時に履歴に保存する関数
# 引数: 実行するコマンドと引数 (例: save_history ls -la)
# 戻り値: 実行したコマンドの終了ステータス
# 動作:
#   - コマンドを実行し、終了ステータスをキャプチャ
#   - 成功(0)、SIGINT(130)、SIGPIPE(141) の場合のみ履歴に保存
#   - それ以外のエラーの場合は履歴に保存しない
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

# ディレクトリをインクリメンタル検索で選択し、移動する関数
# fdad コマンドで検索したディレクトリ一覧から選択
# プレビューでは eza でディレクトリツリーを表示
# 引数: なし
# 戻り値: cd コマンドの終了ステータス
# 参考: https://qiita.com/kamykn/items/aa9920f07487559c0c7e
function fcd-down() {
  local dir
  dir=$(fdad | filter --preview 'eza -T --color=always {} | head -100' +m) &&
  cd "$dir"
}

# 関数・エイリアス名をインクリメンタル検索で選択し、コマンドラインに挿入する関数
# 引数: なし
# 戻り値: なし
# 動作:
#   - システム内部の関数 (先頭が _, -, falias や記号を含むもの) を除外
#   - 関数とエイリアスの一覧から選択
#   - 選択した名前をコマンドラインバッファに挿入 (print -z)
function falias() {
  local funcs aliases selected
  funcs=$(print -l ${(k)functions} | grep -Ev '^(_|-|falias)|[+.:/]')
  aliases=$(alias | cut -d'=' -f1)
  selected=$((echo "$funcs"; echo "$aliases") | sort | uniq | filter --exact --reverse --no-sort --cycle --prompt="関数/エイリアス > ")
  if [[ -n "$selected" ]]; then
    print -z "$selected"
  fi
}

alias fa='falias'