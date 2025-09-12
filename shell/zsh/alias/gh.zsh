#!/bin/zsh
# GitHub CLI aliases

gh config set editor "nvim"

alias ghb='gh browse'
function ghpc() {
  gh pr create --web --body="" "$@"
}
alias -g ghpv='gh pr view --web'
alias -g ghco='gh co'
alias gh-dash='no_notify gh dash'
alias ghd='gh-dash'
alias ghf='no_notify gh f'
alias ghf-gha='ghf -r'
alias ghf-grep-file-history='ghf -g'
alias ghf-branch='ghf -b'
alias ghf-config='ghf -e'
alias ghf-pick='ghf -k'
alias ghf-logs='ghf -l'
alias ghf-prs='ghf -p'

# デフォルトの30件だと少ないので増やして取得
function ghpl(){
  gh pr list -L 200 "${@}"
}
alias ghplm='ghpl --author @me'
alias ghplw='ghpl --web'
alias ghplmw='ghplw --author @me'

# マージ先のブランチ名を表示するPR一覧
function ghpl_branch(){
  ghpl --json number,title,author,baseRefName,headRefName "${@}" \
  | jq -r '.[] | [.number, .title, .author.login, .baseRefName, .headRefName] | @tsv'
}

# コミットハッシュからPR情報を検索（マージ先ブランチ付き）
function ghpl_from_commit() {
    if [ $# -ne 1 ]; then
        echo "Usage: ghpr_from_commit <commit-hash>"
        return 1
    fi

    local commit_hash="${1}"

    # PR情報を検索して、マージ先ブランチも含めて表示
    ghpl_branch --search "${commit_hash}" --state all
}

# 引数の2リビジョンを比較するGitHubのcompare urlを開く
gh_compare_url() {
  if [ $# -ne 2 ]; then
    echo "Usage: git_compare_url BASE COMPARE"
    return 1
  fi

  remote_url=$(git remote get-url origin)

  repo_url=$(echo "${remote_url}" | sed -e 's/git@github.com:/https:\/\/github.com\//' -e 's/\.git$//')

  save_history open "${repo_url}/compare/${1}...${2}"
}