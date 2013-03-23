;; 現在行を目立たせる
(global-hl-line-mode)

;; カーソルの位置が何文字目かを表示する
(column-number-mode t)

;; カーソルの位置が何行目かを表示する
(global-linum-mode)

;; カーソルの場所を保存する
(require 'saveplace)
(setq-default save-place t)
(show-paren-mode 1)
(setq show-paren-delay 0)
(setq show-paren-style 'expression)
(set-face-attribute 'show-paren-match-face nil
                    :background nil :foreground nil
                    :underline "#ffff00" :weight 'extra-bold)

;; バックアップファイルを作らない
(setq make-backup-files nil)
(setq auto-save-default nil)

;; 終了時にオートセーブファイルを消す
(setq delete-auto-save-files t)

(setq indent-line-function 'indent-relative-maybe)
;;Returnキーで改行＋オートインデント
(global-set-key "\C-m" 'newline-and-indent)
;; Returnキーで改行＋オートインデント＋コメント行
;(global-set-key "\C-m" 'indent-new-comment-line)

;;インデントはタブにする
(setq indent-tabs-mode t)
;; tab ではなく space を使う
;(setq-default indent-tabs-mode nil)
;;インデント幅
;(setq c-basic-offset 1)
;;タブ幅
(setq-default tab-width 4)
(setq default-tab-width 4)
(setq tab-stop-list '(4 8 12 16 20 24 28 32 36 40 44 48 52 56 60
                      64 68 72 76 80 84 88 92 96 100 104 108 112 116 120))

;;リージョンをハイライトする
(setq-default transient-mark-mode t)

 (when (>= emacs-major-version 23)
 (setq fixed-width-use-QuickDraw-for-ascii t)
 (setq mac-allow-anti-aliasing t)
 (set-face-attribute 'default nil
                     :family "monaco"
                     :height 140)
 (set-fontset-font
  (frame-parameter nil 'font)
  'japanese-jisx0208
  '("Hiragino Maru Gothic Pro" . "iso10646-1"))
 (set-fontset-font
  (frame-parameter nil 'font)
  'japanese-jisx0212
  '("Hiragino Maru Gothic Pro" . "iso10646-1"))
 (set-fontset-font
  (frame-parameter nil 'font)
  'katakana-jisx0201
  '("Hiragino Maru Gothic Pro" . "iso10646-1"))
 ;; Unicode フォント
 (set-fontset-font
  (frame-parameter nil 'font)
  'mule-unicode-0100-24ff
  '("monaco" . "iso10646-1"))
;; キリル，ギリシア文字設定
;; 注意： この設定だけでは古代ギリシア文字、コプト文字は表示できない
;; http://socrates.berkeley.edu/~pinax/greekkeys/NAUdownload.html が必要
;; キリル文字
 (set-fontset-font
  (frame-parameter nil 'font)
  'cyrillic-iso8859-5
  '("monaco" . "iso10646-1"))
;; ギリシア文字
 (set-fontset-font
  (frame-parameter nil 'font)
  'greek-iso8859-7
  '("monaco" . "iso10646-1"))
 (setq face-font-rescale-alist
       '(("^-apple-hiragino.*" . 1.2)
         (".*osaka-bold.*" . 1.2)
         (".*osaka-medium.*" . 1.2)
         (".*courier-bold-.*-mac-roman" . 1.0)
         (".*monaco cy-bold-.*-mac-cyrillic" . 0.9)
         (".*monaco-bold-.*-mac-roman" . 0.9)
         ("-cdac$" . 1.3))))
;(set-background-color "#98bc98") ;; background color
;(set-background-color "black") ;; background colo
;(set-foreground-color "black")   ;; font color

;; 言語を日本語にする
(set-language-environment 'Japanese)
;; 極力UTF-8とする
(prefer-coding-system 'utf-8)



;;保存時に行末の空白を全て削除
;;from http://d.hatena.ne.jp/tototoshi/20101202/1291289625
(add-hook 'before-save-hook 'delete-trailing-whitespace)

;; from http://piro.hatenablog.com/entry/20101216/1292506110
(require 'wdired)
(define-key dired-mode-map "r" 'wdired-change-to-wdired-mode)

;;from http://www.bookshelf.jp/soft/meadow_28.html#SEC370
(iswitchb-mode 1)

;;from http://d.hatena.ne.jp/ama-ch/20090114/1231918903
;; カーソル位置から行頭まで削除する
(defun backward-kill-line (arg)
  "Kill chars backward until encountering the end of a line."
  (interactive "p")
  (kill-line 0))
;; C-S-kに設定
(global-set-key (kbd "C-S-k") 'backward-kill-line)

;; http://d.hatena.ne.jp/gifnksm/20100131/1264956220
(defun beginning-of-visual-indented-line (current-point)
  "インデント文字を飛ばした行頭に戻る。ただし、ポイントから行頭までの間にインデント文 字しかない場合は、行頭に戻る。"
  (interactive "d")
  (let ((vhead-pos (save-excursion (progn (beginning-of-visual-line) (point))))
        (head-pos (save-excursion (progn (beginning-of-line) (point)))))
    (cond
     ;; 物理行の1行目にいる場合
     ((eq vhead-pos head-pos)
      (if (string-match
           "^[ \t]+$"
           (buffer-substring-no-properties vhead-pos current-point))
          (beginning-of-visual-line)
        (back-to-indentation)))
     ;; 物理行の2行目以降の先頭にいる場合
     ((eq vhead-pos current-point)
      (backward-char)
      (beginning-of-visual-indented-line (point)))
     ;; 物理行の2行目以降の途中にいる場合
     (t (beginning-of-visual-line)))))

(global-set-key "\C-a" 'beginning-of-visual-indented-line)
(global-set-key "\C-e" 'end-of-visual-line)

;; C-kで行全体を削除
(setq kill-whole-line t)

;;http://www.bookshelf.jp/soft/meadow_23.html#SEC231
(ffap-bindings)

;; ツールバーを非表示
;; M-x tool-bar-mode で表示非表示を切り替えられる
(tool-bar-mode -1)


;;import
(add-to-list 'load-path "~/.emacs.d/elisp")

;;for JavaScript & pegjs
;;js2-mode requires Emacs 24.0 or higher.
(autoload 'js2-mode "js2-mode" nil t)
(add-to-list 'auto-mode-alist '("\\.\\(peg\\)?js$" . js2-mode))

;;for Haskell
(autoload 'haskell-mode "haskell-mode-2.8.0/haskell-mode" nil t)
(add-to-list 'auto-mode-alist '("\\.hs$" . haskell-mode))

;;for Scala
(add-to-list 'load-path "~/.emacs.d/elisp/scala-mode2")
(require 'scala-mode2)
;;(autoload 'scala-mode2 "scala-mode2/scala-mode2" nil t)
;;(add-to-list 'auto-mode-alist '("\\.scala$" . scala-mode2))

;;for MiniMap(Sublime Text)
;; from http://www.emacswiki.org/emacs/MiniMap
(require 'minimap)
(global-set-key "\M-m" 'minimap-create)
(global-set-key "\C-\M-m" 'minimap-kill)

;; for Helm(Anything)
;(require './helm/helm-config)
