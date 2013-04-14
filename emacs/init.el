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
;; Ctrl + jで文のどこからでも改行できるようにする
(defun newline-from-anywhere()
    (interactive)
    (end-of-visual-line)
    (newline-and-indent) )
(global-set-key (kbd "C-j") 'newline-from-anywhere)

;;インデントはタブにする
(setq indent-tabs-mode t)
;; tab ではなく space を使う
;(setq-default indent-tabs-mode nil)
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

;; http://d.hatena.ne.jp/sandai/20120304/p2
;; スタートアップ非表示
(setq inhibit-startup-screen t)
;; scratchの初期メッセージ消去
;; (setq initial-scratch-message "")

;; タイトルバーにファイルのフルパス表示
;;(setq frame-title-format
;;      (format "%%f - Emacs@%s" (system-name)))
(setq frame-title-format
      (format "%%f - Emacs"))
      
;; yes or noをy or n
(fset 'yes-or-no-p 'y-or-n-p)

;; GUIで直接ファイルを開いた場合フレームを作成しない
(add-hook 'before-make-frame-hook
          (lambda ()
            (when (eq tabbar-mode t)
              (switch-to-buffer (buffer-name))
              (delete-this-frame))))

;; scroll settings.
;; http://marigold.sakura.ne.jp/devel/emacs/scroll/index.html
(setq scroll-conservatively 1)
(setq next-screen-context-lines 20)
;; カーソル位置の保存
;; http://www.bookshelf.jp/soft/meadow_31.html
(setq scroll-preserve-screen-position t)

;;from http://d.hatena.ne.jp/ama-ch/20090114/1231918903
;; カーソル位置から行頭まで削除する
(defun backward-kill-line (arg)
  "Kill chars backward until encountering the end of a line."
  (interactive "p")
  (kill-line 0))
;; C-S-kに設定
(global-set-key (kbd "C-S-k") 'backward-kill-line)

;; Eclipseみたいに行全体の削除。本来はCtrl + Shift + Del
(define-key global-map (kbd "s-d") 'kill-whole-line)

;; 一行コピー
;; http://emacswiki.org/emacs/CopyingWholeLines
(defun copy-line (arg)
      "Copy lines (as many as prefix argument) in the kill ring"
      (interactive "p")
      (kill-ring-save (line-beginning-position)
                      (line-beginning-position (+ 1 arg)))
      (message "%d line%s copied" arg (if (= 1 arg) "" "s")))
(define-key global-map (kbd "s-b") 'copy-line)

;;; リージョンを削除できるように
;; http://d.hatena.ne.jp/speg03/20091003/1254571961
(delete-selection-mode t)

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

;; MacのCommand + 十字キーを有効にする
;; http://stackoverflow.com/questions/4351044/binding-m-up-m-down-in-emacs-23-1-1
(global-set-key [s-up] 'beginning-of-buffer)
(global-set-key [s-down] 'end-of-buffer)
(global-set-key [s-left] 'beginning-of-visual-indented-line)
(global-set-key [s-right] 'end-of-visual-line)

;;http://www.bookshelf.jp/soft/meadow_23.html#SEC231
;; ファイルやURLをクリック出来るようにする
(ffap-bindings)

;; ツールバーを非表示
;; M-x tool-bar-mode で表示非表示を切り替えられる
(tool-bar-mode -1)

; server start for emacs-client
; http://d.hatena.ne.jp/syohex/20101224/1293206906
(require 'server)
(unless (server-running-p)
  (server-start))


;;import
(add-to-list 'load-path "~/.emacs.d/elisp")

;; for wc mode
;; http://www.emacswiki.org/emacs/WordCountMode
(require 'wc-mode)

;; for tab mode
;; http://ser1zw.hatenablog.com/entry/2012/12/31/022359
;; http://christina04.blog.fc2.com/blog-entry-170.html
(add-to-list 'load-path "~/.emacs.d/elisp/tabbar")
(require 'tabbar)
(tabbar-mode 1)
;; Firefoxライクなキーバインドに
(global-set-key [(control tab)] 'tabbar-forward)
(global-set-key [(control shift tab)] 'tabbar-backward)
;; タブ上でマウスホイールを使わない
;; (tabbar-mwheel-mode nil)
;; グループを使わない
(setq tabbar-buffer-groups-function nil)
;; 左側のボタンを消す
(dolist (btn '(tabbar-buffer-home-button
               tabbar-scroll-left-button
               tabbar-scroll-right-button))
  (set btn (cons (cons "" nil)
                 (cons "" nil))))
;; M-4 で タブ表示、非表示
(global-set-key "\M-4" 'tabbar-mode)

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

;; for auto-install
;; http://d.hatena.ne.jp/rubikitch/20091221/autoinstall
;; 実行時だけ有効にする
;; (require 'auto-install)
;; (setq auto-install-directory "~/.emacs.d/elisp/temp")
;; (auto-install-update-emacswiki-package-name t)
;; (auto-install-compatibility-setup)             ; 互換性確保

;; http://d.hatena.ne.jp/supermassiveblackhole/20100705/1278320568
;; auto-complete
;; 補完候補を自動ポップアップ
(add-to-list 'load-path "~/.emacs.d/elisp/auto-complete")
(require 'auto-complete)
(global-auto-complete-mode t)
;;(require 'auto-complete-config nil t)
;; (setq ac-dictionary-directories "~/.emacs.d/elisp/ac-dict") ;; 辞書ファイルのディレクトリ

;; http://emacs.tsutomuonoda.com/emacs-anything-el-helm-mode-install/
;; for Helm(Anything)
(add-to-list 'load-path "~/.emacs.d/elisp/helm")
(require 'helm-config)
(global-set-key (kbd "C-c h") 'helm-mini)
;; コマンド補完
(helm-mode 1)


;; http://shnya.jp/blog/?p=477
;; http://emacswiki.org/cgi-bin/emacs/FlyMake
;; flymakeパッケージを読み込み
(require 'flymake)
;; 全てのファイルでflymakeを有効化
(add-hook 'find-file-hook 'flymake-find-file-hook)

;;http://emacswiki.org/cgi-bin/emacs/FlyMake
;; automatically displays the flymake error for the current line in the minibuffer
(require 'flymake-cursor)

;; jump to next error
;; http://www.emacswiki.org/emacs/FlyMake
  (defun my-flymake-show-next-error()
    (interactive)
    (flymake-goto-next-error)
    (flymake-display-err-menu-for-current-line)
    )
(global-set-key "\M-n" 'my-flymake-show-next-error)

;;for C++, C
;; Makefile が無くてもC/C++のチェック
(defun flymake-simple-generic-init (cmd &optional opts)
  (let* ((temp-file  (flymake-init-create-temp-buffer-copy
                      'flymake-create-temp-inplace))
         (local-file (file-relative-name
                      temp-file
                      (file-name-directory buffer-file-name))))
    (list cmd (append opts (list local-file)))))

(defun flymake-simple-make-or-generic-init (cmd &optional opts)
  (if (file-exists-p "Makefile")
      (flymake-simple-make-init)
    (flymake-simple-generic-init cmd opts)))

(defun flymake-c-init ()
  (flymake-simple-make-or-generic-init
   "gcc"))
(defun flymake-cc-init ()
  (flymake-simple-make-or-generic-init
   "g++"))
(push '("\\.c\\'" flymake-c-init) flymake-allowed-file-name-masks)
(push '("\\.\\(cc\\|cpp\\|C\\|CPP\\|hpp\\)\\'" flymake-cc-init)
      flymake-allowed-file-name-masks)

;; http://www.info.kochi-tech.ac.jp/y-takata/index.php?%A5%E1%A5%F3%A5%D0%A1%BC%2Fy-takata%2FFlymake
;;for Java
(defun flymake-java-init ()
  (flymake-simple-make-init-impl
   'flymake-create-temp-with-folder-structure nil nil
   buffer-file-name
   'flymake-get-java-cmdline))
(defun flymake-get-java-cmdline (source base-dir)
  (list "javac" (list "-J-Dfile.encoding=utf-8" "-encoding" "utf-8"
              source)))
(push '("\\.java$" flymake-java-init) flymake-allowed-file-name-masks)
(add-hook 'java-mode-hook '(lambda () (flymake-mode t)))
