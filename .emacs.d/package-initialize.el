(require 'package)
;; MELPAのみ追加
(add-to-list 'package-archives '("melpa" . "http://melpa.milkbox.net/packages/"))
;; Marmaladeを追加
(add-to-list 'package-archives  '("marmalade" . "http://marmalade-repo.org/packages/"))
(package-initialize)

;; パッケージ情報の更新
(package-refresh-contents)

;; インストールするパッケージ
(defvar my/favorite-packages
  '(
    ;;;; flymake
    ; flycheck flymake-jslint

    ;;;; don't  use!
    ; helm
    ; popwin
    ; indent-guide
    ; scala-mode2
    ; tabbar-ruler
    ; wc-mode
    ; yasnippet
    ;; nav

  undo-tree
  buffer-move
  auto-complete
  fuzzy
  ace-jump-mode
  anzu
  bm
  expand-region
  haskell-mode
  hlinum
  multiple-cursors
  point-undo
  rainbow-delimiters
  smartrep
  smooth-scroll
  tabbar
  flycheck
  ;; flycheck-pos-tip
  flymake-cursor
  yasnippet
  web-mode
  ; js2-mode
  emmet-mode
  web-beautify
  js-doc
  php-mode
  magit
  vim-region
  smarty-mode
  ;; linum-relative
  ;; evil
  ;; evil-surround
  powerline
  all-ext
  highlight-symbol
  ag
  recentf-ext
    ))

;; my/favorite-packagesからインストールしていないパッケージをインストール
(dolist (package my/favorite-packages)
  (unless (package-installed-p package)
    (package-install package)))
