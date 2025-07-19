#!/usr/local/bin/zsh

# fzfでdockerコンテナに入る
# https://yiskw713.hatenablog.com/entry/2022/01/12/200000#fgc-%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%A9%E3%82%AF%E3%83%86%E3%82%A3%E3%83%96%E3%81%ABgit-checkout%E3%81%99%E3%82%8B
function fdocker-container() {
  local cid
  cid=$(docker ps | sed 1d | fzf -q "$1" | awk '{print $1}')
  [ -n "$cid" ] && docker exec -it "$cid" sh
}

# fzfでdockerのログを取得
# https://yiskw713.hatenablog.com/entry/2022/01/12/200000#fgc-%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%A9%E3%82%AF%E3%83%86%E3%82%A3%E3%83%96%E3%81%ABgit-checkout%E3%81%99%E3%82%8B
function fdocker-log() {
  local cid
  cid=$(docker ps -a | sed 1d | fzf -q "$1" | awk '{print $1}')
  [ -n "$cid" ] && docker logs -f --tail=200 "$cid"
}