;;; 現在行を目立たせる
(global-hl-line-mode)

;;; カーソルの位置が何文字目かを表示する
(column-number-mode t)

;;; カーソルの位置が何行目かを表示する
(line-number-mode t)

;;; カーソルの場所を保存する
(require 'saveplace)
(setq-default save-place t)(show-paren-mode 1)

;;; バックアップファイルを作らない
(setq make-backup-files nil)
(setq auto-save-default nil)

;;; 終了時にオートセーブファイルを消す
(setq delete-auto-save-files t)

(setq indent-line-function 'indent-relative-maybe)
;;;;Returnキーで改行＋オートインデント
(global-set-key "\C-m" 'newline-and-indent)
;;;; Returnキーで改行＋オートインデント＋コメント行
;;;(global-set-key "\C-m" 'indent-new-comment-line)

;;c-modeのコーディングスタイル
;(setq c-default-style "linux")
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

 
;; (set-default-font
;;"-*-Osaka-normal-normal-normal-*-12-*-*-*-m-0-iso10646-1") 
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
 ;;; Unicode フォント
 (set-fontset-font
  (frame-parameter nil 'font)
  'mule-unicode-0100-24ff
  '("monaco" . "iso10646-1"))
;;; キリル，ギリシア文字設定
;;; 注意： この設定だけでは古代ギリシア文字、コプト文字は表示できない
;;; http://socrates.berkeley.edu/~pinax/greekkeys/NAUdownload.html が必要
;;; キリル文字
 (set-fontset-font
  (frame-parameter nil 'font)
  'cyrillic-iso8859-5
  '("monaco" . "iso10646-1"))
;;; ギリシア文字
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
;;(set-background-color "#98bc98") ;; background color
;;(set-foreground-color "black")   ;; font color

; 言語を日本語にする
(set-language-environment 'Japanese)
; 極力UTF-8とする
(prefer-coding-system 'utf-8)

; [*.pegjs]ファイルをJavaScriptモードで開く
(setq auto-mode-alist
      (cons (cons "\\.pegjs$" 'js-mode) auto-mode-alist))