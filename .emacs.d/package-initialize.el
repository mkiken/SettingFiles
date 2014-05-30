(require 'package)
;; MELPAのみ追加
(add-to-list 'package-archives '("melpa" . "http://melpa.milkbox.net/packages/"))
(package-initialize)

;; パッケージ情報の更新
(package-refresh-contents)

;; インストールするパッケージ
(defvar my/favorite-packages
  '(
    ;;;; for auto-complete
    ; auto-complete fuzzy popup pos-tip

    ;;;; buffer utils
    ; popwin elscreen yascroll buffer-move

    ;;;; flymake
    ; flycheck flymake-jslint

    ;;;; go
    ; go-mode

    ;;;; python
    ; jedi

    ;;;; helm
    ; helm

    ;;;; git
    ; magit git-gutter

  undo-tree
    ))

;; my/favorite-packagesからインストールしていないパッケージをインストール
(dolist (package my/favorite-packages)
  (unless (package-installed-p package)
    (package-install package)))
