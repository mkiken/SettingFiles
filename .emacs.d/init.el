;; http://d.hatena.ne.jp/tomoya/20090807/1249601308
;;MacとWindowsで場合分け
(defun x->bool (elt) (not (not elt)))

;; system-type predicates
(setq darwin-p  (eq system-type 'darwin)
      ns-p      (eq window-system 'ns)
      carbon-p  (eq window-system 'mac)
      ;; linux-p   (eq system-type 'gnu/linux)
      ;; colinux-p (when linux-p
      ;;             (let ((file "/proc/modules"))
      ;;               (and
      ;;                (file-readable-p file)
      ;;                (x->bool
      ;;                 (with-temp-buffer
      ;;                   (insert-file-contents file)
      ;;                   (goto-char (point-min))
      ;;                   (re-search-forward "^cofuse\.+" nil t))))))
      cygwin-p  (eq system-type 'cygwin)
      nt-p      (eq system-type 'windows-nt)
      meadow-p  (featurep 'meadow)
      windows-p (or cygwin-p nt-p meadow-p))

;; 言語を日本語にする（IME設定より上に置かなければならない）
(set-language-environment 'Japanese)
;; 極力UTF-8とする
(prefer-coding-system 'utf-8)

;; Settings for Mac OS X
(when darwin-p
  ;; key bindings
  ;; Eclipseみたいに行全体の削除。本来はCtrl + Shift + Del
  (define-key global-map (kbd "s-d") 'kill-whole-line)
  (define-key global-map (kbd "s-b") 'copy-line)
  (global-set-key (kbd "s-r") 'revert-buffer)

  ; システムへ修飾キーを渡さない設定
  ; (setq mac-pass-control-to-system nil)
  ; (setq mac-pass-command-to-system nil)
  ; (setq mac-pass-option-to-system nil)

  ; http://blog.n-z.jp/blog/2013-11-12-cocoa-emacs-ime.html
  (when (boundp 'mac-input-method-parameters)
    ;; ime inline patch
	(setq default-input-method "MacOSX")
	;; IMの状態で色を分ける
	(mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Roman" 'cursor-color "OliveDrab4")     ; ことえり ローマ字
	; (mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Roman" 'title "A")     ; ことえり ローマ字
	(mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Japanese" 'cursor-color "LightPink1") ; ことえり 日本語
	(mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Japanese.Katakana" 'cursor-color "LightSkyBlue1") ; ことえり 日本語
	; (mac-set-input-method-parameter "com.google.inputmethod.Japanese.Roman" 'cursor-color "yellow")   ; Google ローマ字
	; (mac-set-input-method-parameter "com.google.inputmethod.Japanese.base" 'cursor-color "magenta")   ; Google 日本語
  	;; backslash を優先
	(mac-translate-from-yen-to-backslash)
	)

  ;; MacのCommand + 十字キーを有効にする
  ;; http://stackoverflow.com/questions/4351044/binding-m-up-m-down-in-emacs-23-1-1
  (global-set-key [s-up] 'beginning-of-buffer)
  (global-set-key [s-down] 'end-of-buffer)
  (global-set-key [s-left] 'beginning-of-visual-indented-line)
  (global-set-key [s-right] 'end-of-visual-line)


  ; http://insideflag.blogspot.jp/2012/10/homebrewcocoa-emacs-242.html
  (setq ns-pop-up-frames nil) ;; 新しいウィンドウでファイルを開かない

  ;; font settings
  (when (>= emacs-major-version 23)
	(setq fixed-width-use-QuickDraw-for-ascii t)
	(setq mac-allow-anti-aliasing t)
	(when (display-graphic-p)
	  (set-face-attribute 'default nil
						  :family "monaco"
						  :height 115)
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
		  	'(("^-apple-hiragino.*" . 1.1)
			  (".*osaka-bold.*" . 1.1)
			  (".*osaka-medium.*" . 1.1)
			  (".*courier-bold-.*-mac-roman" . 0.9)
			  (".*monaco cy-bold-.*-mac-cyrillic" . 0.8)
			  (".*monaco-bold-.*-mac-roman" . 0.8)
			  ("-cdac$" . 1.2)))
	  )
	)

	;; PATH
  (dolist (dir (list
					; "/sbin"
					; "/usr/sbin"
					; "/bin"
					; "/usr/bin"
	        "/usr/local/bin"
	        (expand-file-name "~/bin")
	        ))
    ;; exec-path
    (when (and (file-exists-p dir) (not (member dir exec-path)))
      (setenv "PATH" (concat dir ":" (getenv "PATH")))
      (setq exec-path (append (list dir) exec-path))))

  ;; ag
  (setq ag-highlight-search t)
  (setq ag-reuse-buffers 't)

  )

;; Settings for Windows
(when windows-p
  (set-face-font 'default "Meiryo UI-10")
  ;;; IME の設定
  ;; http://bmonkey.cocolog-nifty.com/blog/2012/07/gnu-emacs-241wi.html
  ;;(setq default-input-method "W32-IME)
  )

;; 現在行を目立たせる
(global-hl-line-mode)

;; カーソルの位置が何文字目かを表示する
(column-number-mode t)

;; カーソルの位置が何行目かを表示する
(global-linum-mode)
; (setq linum-format "%d")
(setq linum-format " %3d")

;; カーソルの場所を保存する
(require 'saveplace)
(setq-default save-place t)
(show-paren-mode 1)
(setq show-paren-delay 0)
(setq show-paren-style 'mixed)

;; ミニバッファの履歴を保存する
(savehist-mode t)
(setq history-length 1000) ;履歴数

; http://wadap.hatenablog.com/entry/20120415/1334468285
(require 'uniquify)
(setq uniquify-buffer-name-style 'forward)

;; バックアップファイルを作らない
; (setq make-backup-files nil)
; (setq auto-save-default nil)
(setq make-backup-files t)

(setq
 backup-by-copying t      ; don't clobber symlinks
 delete-old-versions t
 kept-new-versions 3
 kept-old-versions 2
 version-control t)       ; use versioned backups

(when darwin-p
  (setq
   backup-directory-alist
   '(("." . "~/.backup/emacs/backup/"))    ; don't litter my fs tree
  )
  (setq auto-save-file-name-transforms
        `((".*", (expand-file-name "~/.backup/emacs/autosave/") t)))
  )
(when windows-p
  (setq
   backup-directory-alist
   '(("." . "~/.backup/emacs/backup"))    ; don't litter my fs tree
   )
  (setq auto-save-file-name-transforms
        `((".*", (expand-file-name "~/.backup/emacs/autosave") t)))
  )


; http://stackoverflow.com/questions/5738170/why-does-emacs-create-temporary-symbolic-links-for-modified-files
(setq create-lockfiles nil)

;; 終了時にオートセーブファイルを消す
(setq delete-auto-save-files t)

(setq indent-line-function 'indent-relative-maybe)
;;Returnキーで改行＋オートインデント
(global-set-key "\C-m" 'newline-and-indent)
;(global-set-key "\C-m" 'align-newline-and-indent)
;;(global-set-key "\C-m" 'reindent-then-newline-and-indent)
;; C-jで文のどこからでも改行できるようにする
(defun newline-from-anywhere()
  (interactive)
  (end-of-line)
  (newline-and-indent) )
(global-set-key (kbd "C-j") 'newline-from-anywhere)
(defun backward-newline-from-anywhere()
  (interactive)
  (beginning-of-line)
  (newline-and-indent)
  (previous-line)
  (c-indent-command))
(global-set-key (kbd "C-S-j") 'backward-newline-from-anywhere)


; ダイアログを出さない
(setq use-dialog-box nil)

; http://www.emacswiki.org/emacs/AutoIndentation
(electric-indent-mode 1)

; yankしたテキストを自動整形
(dolist (command '(yank yank-pop))
   (eval `(defadvice ,command (after indent-region activate)
            (and (not current-prefix-arg)
                 (member major-mode '(emacs-lisp-mode lisp-mode
                                                      clojure-mode    scheme-mode
                                                      haskell-mode    ruby-mode
                                                      rspec-mode      python-mode
                                                      c-mode          c++-mode
                                                      objc-mode       latex-mode
                                                      plain-tex-mode  js2-mode
                                                      web-mode        php-mode))
                 (let ((mark-even-if-inactive transient-mark-mode))
                   (indent-region (region-beginning) (region-end) nil))))))

; (global-set-key (kbd "C-<left>")  'windmove-left)

;; http://dev.ariel-networks.com/wp/documents/aritcles/emacs/part16
;;範囲指定していないとき、C-wで前の単語を削除
(defadvice kill-region (around kill-word-or-kill-region activate)
           (if (and (interactive-p) transient-mark-mode (not mark-active))
             (backward-kill-word 1)
             ad-do-it))
;; minibuffer用
(define-key minibuffer-local-completion-map "\C-w" 'backward-kill-word)
;; カーソル位置の単語を削除
; (defun kill-word-at-point ()
  ; (interactive)
  ; (let ((char (char-to-string (char-after (point)))))
    ; (cond
      ; ((string= " " char) (delete-horizontal-space))
      ; ((string-match "[\t\n -@\[-`{-~]" char) (kill-word 1))
      ; (t (forward-char) (backward-word) (kill-word 1)))))
; (global-set-key "\M-d" 'kill-word-at-point)

;; kill-lineで行が連結したときにインデントを減らす
(defadvice kill-line (before kill-line-and-fixup activate)
           (when (and (not (bolp)) (eolp))
             (forward-char)
             (fixup-whitespace)
             (backward-char)))

; http://macemacsjp.sourceforge.jp/index.php?CocoaEmacs#fc72ad9e
; フォントサイズ変更
(global-set-key (kbd "C-c +") (lambda () (interactive) (text-scale-increase 1)))
(global-set-key (kbd "C-c -") (lambda () (interactive) (text-scale-decrease 1)))
(global-set-key (kbd "C-c 0") (lambda () (interactive) (text-scale-increase 0)))

; C-hをbackspaceとして使用する
; http://akisute3.hatenablog.com/entry/20120318/1332059326
(keyboard-translate ?\C-h ?\C-?)
(define-key global-map (kbd "C-c h") 'help-command)

; (define-key global-map (kbd "C-c g") 'grep-find)
(define-key global-map (kbd "C-c g") 'ag)
(define-key global-map (kbd "C-c t") 'sr-speedbar-select-window)

; 削除ファイルをゴミ箱に入れる
(setq delete-by-moving-to-trash t)
(setq trash-directory "~/.Trash")

; ファイル名補完機能で大文字と小文字の区別をなくす
(setq read-buffer-completion-ignore-case t)
(setq read-file-name-completion-ignore-case t)
;;; 補完時に大文字小文字を区別しない
(setq completion-ignore-case t)

;; M-dで単語のどこからでも削除できるようにする
;(defun kill-word-from-anywhere()
;  (interactive)
;  (forward-char)
;  (backward-word)
;  (kill-word 1) )
;(global-set-key (kbd "M-d") 'kill-word-from-anywhere)

;; Window間の移動をM-...でやる
;; http://www.emacswiki.org/emacs/WindMove
; (windmove-default-keybindings 'super)

(global-set-key (kbd "C-x <left>")  'windmove-left)
(global-set-key (kbd "C-x <right>")  'windmove-right)
(global-set-key (kbd "C-x <up>")  'windmove-up)
(global-set-key (kbd "C-x <down>")  'windmove-down)
(global-set-key (kbd "C-x =")  'balance-windows)

; http://www.geocities.co.jp/SiliconValley-Bay/9285/EMACS-JA/emacs_165.html
(setq split-window-keep-point nil)

;; tab ではなく space を使う
(setq-default indent-tabs-mode nil)
;;タブ幅
(setq-default tab-width 2)
; (setq default-tab-width 2)
(setq tab-stop-list '(2 4 8 12 16 20 24 28 32 36 40 44 48 52 56 60 64 68 72 76 80 84 88 92 96 100 104 108 112 116 120))
;; http://reiare.net/blog/2010/12/16/emacs-space-tab/
;; 最後に改行を入れる。
(setq require-final-newline t)

;; 行末の空白を表示
(setq-default show-trailing-whitespace t)

; http://qiita.com/itiut@github/items/4d74da2412a29ef59c3a
(require 'whitespace)
(setq whitespace-style '(face           ; faceで可視化
                          trailing       ; 行末
                          tabs           ; タブ
                          spaces         ; スペース
                          empty          ; 先頭/末尾の空行
                          space-mark     ; 表示のマッピング
                          tab-mark
                          ))

; http://ergoemacs.org/emacs/whitespace-mode.html
(setq whitespace-display-mappings
      '((space-mark ?\u3000 [?\u25a1])
        ; (space-mark   ?\    [?\xB7]     [?.])	; space
        ; (space-mark   ?\xA0 [?\xA4]     [?_])	; hard space
        ; (newline-mark ?\n   [?\xB6 ?\n] [?$ ?\n])	; end-of-line
        ; (tab-mark ?\t [?\u00BB ?\t] [?\\ ?\t])
        (tab-mark 9 [183 9] [92 9])
        ))

;; スペースは全角のみを可視化
(setq whitespace-space-regexp "\\(\u3000+\\)")

;; 保存前に自動でクリーンアップ
(setq whitespace-action '(auto-cleanup))

;;保存時に行末の空白を全て削除
;;from http://d.hatena.ne.jp/tototoshi/20101202/1291289625
; (add-hook 'before-save-hook 'delete-trailing-whitespace)

;;http://masutaka.net/chalow/2011-10-12-1.html
(global-whitespace-mode 1)

;; http://d.hatena.ne.jp/kakurasan/20070702/p1

(add-hook 'dired-load-hook
          '(lambda ()
             ;; ディレクトリを再帰的にコピー可能にする
             (setq dired-recursive-copies 'always)
             ;; ディレクトリを再帰的に削除可能にする(使用する場合は注意)
             ;(setq dired-recursive-deletes 'always)
             ;; lsのオプション 「l」(小文字のエル)は必須
             (setq dired-listing-switches "-Flha") ; 「.」と「..」が必要な場合
             ;(setq dired-listing-switches "-GFlhA") ; グループ表示が不要な場合
             ;(setq dired-listing-switches "-FlhA")
             ;; find-dired/find-grep-diredで、条件に合ったファイルをリストする形式
             ;(setq find-ls-option '("-print0 | xargs -0 ls -Flhatd"))
             ;; 無効コマンドdired-find-alternate-fileを有効にする
             (put 'dired-find-alternate-file 'disabled nil)
             )
          )
;; ファイル・ディレクトリ名のリストを編集することで、まとめてリネーム可能にする
(require 'wdired)
;; wdiredモードに入るキー(下の例では「r」)
(define-key dired-mode-map "r" 'wdired-change-to-wdired-mode)
;; 新規バッファを作らずにディレクトリを開く(デフォルトは「a」)
(define-key dired-mode-map (kbd "RET") 'dired-find-alternate-file)
;; 「a」を押したときに新規バッファを作って開くようにする
(define-key dired-mode-map "a" 'dired-advertised-find-file)
;; 「^」が押しにくい場合「c」でも上の階層に移動できるようにする
(define-key dired-mode-map "c" 'dired-up-directory)

;; http://d.hatena.ne.jp/sandai/20120304/p2
;; スタートアップ非表示
(setq inhibit-startup-screen t)
;; scratchの初期メッセージ消去
;; (setq initial-scratch-message "")

;; タイトルバーにファイルのフルパス表示
(setq frame-title-format
      (format "%%f - Emacs@%s" (system-name)))

;; yes or noをy or n
(fset 'yes-or-no-p 'y-or-n-p)

;; GUIで直接ファイルを開いた場合フレームを作成しない
; (add-hook 'before-make-frame-hook
; (lambda ()
; (when (eq tabbar-mode t)
; (switch-to-buffer (buffer-name))
; (delete-this-frame))))


;; scroll settings.
;; http://marigold.sakura.ne.jp/devel/emacs/scroll/index.html
(setq scroll-conservatively 1) ;画面の下端で↓向きに1行移動したり，上端で↑向きに1行移動したりしたときのスクロール量を1に設定する．
(setq next-screen-context-lines 20) ;1画面スクロールしたときに以前の画面を何行分残すかを設定する． 0だとまったく残さない．
; (setq scroll-step 1)

(defun my-scroll-down (arg)
  (interactive "p")
  (scroll-down-line 15))
(defun my-scroll-up (arg)
  (interactive "p")
  (scroll-up-line 15))
(global-set-key (kbd "M-v") 'my-scroll-down)
(global-set-key (kbd "C-v") 'my-scroll-up)

(global-set-key (kbd "C-S-v") 'scroll-up-line)
(global-set-key (kbd "M-V") 'scroll-down-line)
(global-set-key (kbd "C-<down>") 'scroll-up-line)
(global-set-key (kbd "C-<up>") 'scroll-down-line)
;; カーソル位置の保存
;; http://www.bookshelf.jp/soft/meadow_31.html
(setq scroll-preserve-screen-position t)

; settings for org-mode.
; ファイルを開いた時は畳んだ状態で表示
(setq org-startup-folded nil)
; 長い行を折り返し
; http://d.hatena.ne.jp/stakizawa/20091025/t1
(setq org-startup-truncated nil)
; font-lock を有効化
; (add-hook 'org-mode-hook 'turn-on-font-lock)




;; avoid "Symbolic link to SVN-controlled source file; follow link? (yes or no)"
; http://openlab.dino.co.jp/2008/10/30/212934368.html
(setq vc-follow-symlinks t)

; http://stackoverflow.com/questions/4096580/how-to-make-emacs-reload-the-tags-file-automatically
(defalias 'yes-or-no-p 'y-or-n-p)

; http://www.masteringemacs.org/articles/2010/11/14/disabling-prompts-emacs/
(setq confirm-nonexistent-file-or-buffer nil)
(setq kill-buffer-query-functions
      (remq 'process-kill-buffer-query-function
            kill-buffer-query-functions))

(setq revert-without-query '(".*"))
(global-auto-revert-mode 1)

;;from http://d.hatena.ne.jp/ama-ch/20090114/1231918903
;; カーソル位置から行頭まで削除する
(defun backward-kill-line (arg)
  "Kill chars backward until encountering the end of a line."
  (interactive "p")
  (kill-line 0))
;; C-S-kに設定
(global-set-key (kbd "C-S-k") 'backward-kill-line)
(global-set-key (kbd "M-S-k") 'backward-kill-sentence)

(defun backward-mark-paragraph (arg)
  (interactive "p")
  (mark-paragraph (- arg) 1)
  )
(global-set-key (kbd "M-H") 'backward-mark-paragraph)
(defun backward-kill-sentence (arg)
  (interactive "p")
  (kill-sentence (- arg))
  )
(global-set-key (kbd "M-K") 'backward-kill-sentence)
(global-set-key (kbd "C-c k") 'kill-paragraph)
(global-set-key (kbd "C-c K") 'backward-kill-paragraph)

;; 一行コピー
;; http://emacswiki.org/emacs/CopyingWholeLines
(defun copy-line (arg)
  "Copy lines (as many as prefix argument) in the kill ring"
  (interactive "p")
  (kill-ring-save (line-beginning-position)
				  (line-beginning-position (+ 1 arg)))
  (message "%d line%s copied." arg (if (= 1 arg) "" "s")))

(defun copy-oneline (arg)
  "Copy line"
  (interactive "p")
  (kill-ring-save (line-beginning-position)
				  (line-end-position))
  (message "1 line copied."))

(global-set-key (kbd "C-,") 'copy-line)
(global-set-key (kbd "C-.") 'kill-whole-line)

;; viのpのように改行してヤンク
(defun vi-p ()
  (interactive)
  (end-of-line)
  (newline-and-indent)
  (yank)
  )
(global-set-key (kbd "C-:") 'vi-p)

;; 一行コメント
;; http://d.hatena.ne.jp/tomoya/20091015/1255593575
(defun oneline-comment (current-point)
  (interactive "d")
  (let ((head-pos (save-excursion (progn (beginning-of-line) (point))))
        (tail-pos (save-excursion (progn (end-of-line) (point)))))
    (comment-or-uncomment-region head-pos tail-pos)))
(global-set-key (kbd "C-;") 'oneline-comment)

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

(global-set-key (kbd "M-<up>")  'backward-paragraph)
(global-set-key (kbd "M-<down>")  'forward-paragraph)

;; MacのC-f4対策
(global-set-key (kbd "<C-f4>") 'ns-do-hide-emacs)

;; 範囲置換
;;(global-set-key (kbd "C-c r") 'replace-regexp)
(global-set-key (kbd "C-c r") 'replace-string)

;; 行に飛ぶ
(global-set-key (kbd "C-c l") 'goto-line)
(global-set-key (kbd "C-c o 1") 'occur)
(global-set-key (kbd "C-c o 2") 'multi-occur-in-matching-buffers)
(global-set-key (kbd "C-c o 3") 'helm-occur)
(global-set-key (kbd "C-c o 4") 'helm-multi-occur)
(global-set-key (kbd "C-c v") 'revert-buffer)

; http://shibayu36.hatenablog.com/entry/2012/12/04/111221
;;; 複数行移動
(global-set-key "\M-n" (kbd "C-u 5 C-n"))
(global-set-key "\M-p" (kbd "C-u 5 C-p"))

;; VC++のC-f3(FindNextSelected)みたいなiSearch
;; http://dev.ariel-networks.com/articles/emacs/part5/
(defadvice isearch-mode (around isearch-mode-default-string (forward &optional regexp op-fun recursive-edit word-p) activate)
           (if (and transient-mark-mode mark-active (not (eq (mark) (point))))
             (progn
               (isearch-update-ring (buffer-substring-no-properties (mark) (point)))
               (deactivate-mark)
               ad-do-it
               (if (not forward)
                 (isearch-repeat-backward)
                 (goto-char (mark))
                 (isearch-repeat-forward)))
             ad-do-it))
(define-key isearch-mode-map (kbd "C-c o") 'isearch-occur)


;;http://flex.ee.uec.ac.jp/texi/faq-jp/faq-jp_130.html
;; By an unknown contributor
; (defun match-paren (arg)
; "Go to the matching parenthesis if on parenthesis otherwise insert %."
; (interactive "p")
; (cond ((looking-at "\\s\(") (forward-list 1) (backward-char 1))
; ((looking-at "\\s\)") (forward-char 1) (backward-list 1))
; (t (self-insert-command (or arg 1)))))
; (global-set-key C-](kbd "C-]") 'match-paren)

; https://gist.github.com/takehiko/4107554
;; 対応するカッコにジャンプ
(defun match-paren-japanese (arg)
  "Go to the matching parenthesis."
  (interactive "p")
  (cond ((looking-at "[([{（｛［「『《〔【〈]") (forward-sexp 1) (backward-char))
        ((looking-at "[])}）｛］」』》〕】〉]") (forward-char) (backward-sexp 1))
        (t (message "match-paren-japanese ignored"))))
(global-set-key (kbd "C-]") 'match-paren-japanese)
;; 対応するカッコまでをコピー
(defun match-paren-kill-ring-save ()
  "Copy region from here to the matching parenthesis to kill ring and save."
  (interactive)
  (set-mark-command nil)
  (match-paren-japanese nil)
  (forward-char)
  (exchange-point-and-mark)
  ; (clipboard-kill-ring-save (mark) (point))
  ; (let ((c (abs (- (mark) (point)))))
    ; (message "match-paren-kill-ring-save: %d characters saved" c))
  )
(global-set-key (kbd "C-}") 'match-paren-kill-ring-save)

; http://qiita.com/ShingoFukuyama/items/fc51a32e84fd84261565
(defun move-line (arg)
  (let ((col (current-column)))
    (save-excursion
      (forward-line)
      (transpose-lines arg))
    (when (> arg 0)
      (forward-line arg))
    (move-to-column col)))

; (global-set-key (kbd "M-N") (lambda () (interactive) (move-line 3)))
(global-set-key (kbd "C-S-t") (lambda () (interactive) (move-line -1)))
(global-set-key (kbd "M-T") (lambda () (interactive) (move-line 1)))

;; http://d.hatena.ne.jp/mooz/20100119/p1
(defun window-resizer ()
  "Control window size and position."
  (interactive)
  (let ((window-obj (selected-window))
        (current-width (window-width))
        (current-height (window-height))
        (dx (if (= (nth 0 (window-edges)) 0) 1
              -1))
        (dy (if (= (nth 1 (window-edges)) 0) 1
              -1))
        c)
    (catch 'end-flag
           (while t
                  (message "size[%dx%d]"
                           (window-width) (window-height))
                  (setq c (read-char))
                  (cond ((= c ?l)
                         (enlarge-window-horizontally dx))
                        ((= c ?h)
                         (shrink-window-horizontally dx))
                        ((= c ?j)
                         (enlarge-window dy))
                        ((= c ?k)
                         (shrink-window dy))
                        ;; otherwise
                        (t
                          (message "Quit")
                          (throw 'end-flag t)))))))
(global-set-key "\C-c\C-r" 'window-resizer)

; http://stackoverflow.com/questions/2706527/make-emacs-stop-asking-active-processes-exist-kill-them-and-exit-anyway
(defadvice save-buffers-kill-emacs (around no-query-kill-emacs activate)
  "Prevent annoying \"Active processes exist\" query when you quit Emacs."
  (flet ((process-list ())) ad-do-it))

; http://d.hatena.ne.jp/a_bicky/20131221/1387623058
(if (>= emacs-major-version 24)
  (progn
    ; 括弧の対応
    (electric-pair-mode t)
    (defadvice electric-pair-post-self-insert-function
               (around electric-pair-post-self-insert-function-around activate)
               "Don't insert the closing pair in comments or strings"
               (unless (nth 8 (save-excursion (syntax-ppss (1- (point)))))
                 ad-do-it))

    ; http://stackoverflow.com/questions/2951797/wrapping-selecting-text-in-enclosing-characters-in-emacs
    ; (global-set-key (kbd "(") 'insert-pair)
    ; (global-set-key (kbd "{") 'insert-pair)
    ; (global-set-key (kbd "[") 'insert-pair)
    ; (global-set-key (kbd "\"") 'insert-pair)
    ; (global-set-key (kbd "'") 'insert-pair)
    ; (global-set-key (kbd "M-(") 'delete-pair)
    )
  ;; Setup the alternative manually.
  (progn
    ; http://metalphaeton.blogspot.jp/2011/04/emacs.html
    ; http://ggorjan.blogspot.jp/2007/05/skeleton-pair-mode-in-emacs.html
    (global-set-key (kbd "(") 'skeleton-pair-insert-maybe)
    (global-set-key (kbd "{") 'skeleton-pair-insert-maybe)
    (global-set-key (kbd "[") 'skeleton-pair-insert-maybe)
    (global-set-key (kbd "\"") 'skeleton-pair-insert-maybe)
    (setq skeleton-pair 1)
    (setq skeleton-pair-on-word t) ; apply skeleton trick even in front of a word.
    )
  )

  ; http://ergoemacs.org/emacs/emacs_insert_brackets_by_pair.html
(defun insert-bracket-pair (leftBracket rightBracket)
  "Insert a matching bracket.
  If region is not active, place the cursor between them.
  If region is active, insert around the region, place the cursor after the right bracket.

  The argument leftBracket rightBracket are strings."
  (if (region-active-p)
    (let (
          (p1 (region-beginning))
          (p2 (region-end))
          )
      (goto-char p2)
      (insert rightBracket)
      (goto-char p1)
      (insert leftBracket)
      (goto-char (+ p2 2))
      )
    (progn
      (insert leftBracket rightBracket)
      (backward-char 1) ) )
  )
(defun insert-pair-paren () (interactive) (insert-bracket-pair "(" ")") )
(global-set-key "(" 'insert-pair-paren)
(defun insert-pair-bracket () (interactive) (insert-bracket-pair "[" "]") )
(global-set-key "[" 'insert-pair-bracket)
(defun insert-pair-brace () (interactive) (insert-bracket-pair "{" "}") )
(global-set-key "{" 'insert-pair-brace)
(defun insert-pair-double-straight-quote () (interactive) (insert-bracket-pair "\"" "\"") )
(global-set-key "\"" 'insert-pair-double-straight-quote)
(defun insert-pair-single-straight-quote () (interactive) (insert-bracket-pair "'" "'") )
(global-set-key "'" 'insert-pair-single-straight-quote)
(defun insert-pair-single-angle-quote () (interactive) (insert-bracket-pair "‹" "›") )
(global-set-key "‹" 'insert-pair-single-angle-quote)
(defun insert-pair-double-angle-quote () (interactive) (insert-bracket-pair "«" "»") )
(global-set-key "«" 'insert-pair-double-angle-quote)
(defun insert-pair-double-curly-quote () (interactive) (insert-bracket-pair "“" "”") )
(global-set-key "“" 'insert-pair-double-curly-quote)
(defun insert-pair-single-curly-quote () (interactive) (insert-bracket-pair "‘" "’") )
(global-set-key "‘" 'insert-pair-single-curly-quote)
(defun insert-pair-corner-bracket () (interactive) (insert-bracket-pair "「" "」") )
(global-set-key "「" 'insert-pair-corner-bracket)
(defun insert-pair-white-corner-bracket () (interactive) (insert-bracket-pair "『" "』") )
(global-set-key "『" 'insert-pair-white-corner-bracket)
(defun insert-pair-angle-bracket () (interactive) (insert-bracket-pair "〈" "〉") )
(global-set-key "〈" 'insert-pair-angle-bracket)
(defun insert-pair-double-angle-bracket () (interactive) (insert-bracket-pair "《" "》") )
(global-set-key "《" 'insert-pair-double-angle-bracket)
(defun insert-pair-white-lenticular-bracket () (interactive) (insert-bracket-pair "〖" "〗") )
(global-set-key "〖" 'insert-pair-white-lenticular-bracket)
(defun insert-pair-black-lenticular-bracket () (interactive) (insert-bracket-pair "【" "】") )
(global-set-key "【" 'insert-pair-black-lenticular-bracket)
(defun insert-pair-tortoise-shell-bracket () (interactive) (insert-bracket-pair "〔" "〕") )
(global-set-key "〔" 'insert-pair-black-tortoise-shell-bracket)

; http://www.emacswiki.org/emacs/AutoPairs

;起動時のフレームサイズを設定する
(setq initial-frame-alist
	  (append (list
                ;        '(width . 130)
                ;        '(height . 35)
		        '(alpha . (95 90)) ;; 透明度。(アクティブ時, 非アクティブ時)
				)
			  initial-frame-alist))
(setq default-frame-alist initial-frame-alist)

;;http://www.bookshelf.jp/soft/meadow_23.html#SEC231
;; ファイルやURLをクリック出来るようにする
(ffap-bindings)

;; ffap を使っていて find-file-at-point を起動した場合に、カーソル位置の UNC が正しく
;; 取り込まれないことの対策
; (defadvice helm-completing-read-default-1 (around ad-helm-completing-read-default-1 activate)
; (if (listp (ad-get-arg 4))
; (ad-set-arg 4 (car (ad-get-arg 4))))
; ;; (cl-letf (((symbol-function 'regexp-quote)
; (letf (((symbol-function 'regexp-quote)
; (symbol-function 'identity)))
; ad-do-it))

;; ツールバーを非表示
;; M-x tool-bar-mode で表示非表示を切り替えられる
(tool-bar-mode -1)
;;; emacs -nw で起動した時にメニューバーを消す
(if window-system (menu-bar-mode 1) (menu-bar-mode -1))
;;; 現在の関数名をモードラインに表示
(which-function-mode 1)

; http://superuser.com/questions/349943/how-to-awake-emacs-gui-after-pressing-ctrlz
(when window-system (global-unset-key (kbd "C-z")))

;; enable to pop `mark-ring' repeatedly like C-u C-SPC C-SPC ...
(setq set-mark-command-repeat-pop t)

;; 矩形選択
;; http://dev.ariel-networks.com/articles/emacs/part5/
(cua-mode t)
(setq cua-enable-cua-keys nil)

;;; ediffを1ウィンドウで実行
(setq ediff-window-setup-function 'ediff-setup-windows-plain)
;; diffのバッファを上下ではなく左右に並べる
(setq ediff-split-window-function 'split-window-horizontally)

;; server start for emacs-client
;; http://d.hatena.ne.jp/syohex/20101224/1293206906
(require 'server)
(unless (server-running-p)
  (server-start))

;;; リージョンの大文字小文字変換を有効にする。
;; C-x C-u -> upcase
;; C-x C-l -> downcase
(put 'upcase-region 'disabled nil)
(put 'downcase-region 'disabled nil)

; (setq-default flyspell-mode t)
; (setq ispell-dictionary "american")

; http://d.hatena.ne.jp/kitokitoki/20100425/p1
;;Warning: `mapcar' called for effect; use `mapc' or `dolist' instead を防ぐ
; (setq byte-compile-warnings '(free-vars unresolved callargs redefine obsolete noruntime cl-functions interactive-only make-local unused))

;;import
(add-to-list 'load-path "~/.emacs.d/elisp")
; (add-to-list 'load-path "~/.emacs.d/elpa")

; package.elの設定
(require 'package)
(add-to-list 'package-archives '("melpa" . "http://melpa.milkbox.net/packages/"))
;; Marmaladeを追加
(add-to-list 'package-archives  '("marmalade" . "http://marmalade-repo.org/packages/"))
(package-initialize)

; http://www.emacswiki.org/emacs/ColorThemeQuestions
; 端末だと色が足りなくてthemeがきれいに動かない
; 一応export TERM=xterm-256colorでいけるけど・・・？
; (when window-system
(when 1
  ; (load "~/.emacs.d/conf/window-system")
  ;; Color Scheme
  (add-to-list 'custom-theme-load-path "~/.emacs.d/themes")
  (load-theme 'my-monokai t)
  ;; (load-theme 'monokai t)
  ;; (load-theme 'molokai t)
  ; (load-theme 'monokai-dark-soda t)
  ; (load-theme 'zenburn t)
  ; (load-theme 'solarized-light t)
	; (load-theme 'solarized-dark t)
  ; (load-theme 'twilight-anti-bright t)
  ; (load-theme 'tomorrow-night-paradise t)
  ; (load-theme 'tomorrow-night-blue t)
  ; (load-theme 'tomorrow-night-bright t)
  ; (load-theme 'tomorrow-night-eighties t)
  ; (load-theme 'tomorrow-night t)
  ;; (load-theme 'tomorrow t)
  ;; (load-theme 'twilight-bright t)
  ; (load-theme 'espresso t)
; https://github.com/emacs-jp/replace-colorthemes/blob/master/subdued-theme.el
 ; (load-theme 'aliceblue t)
 ; (load-theme 'charcoal-black t)
 ; (load-theme 'dark-gnus t)
 ; (load-theme 'ramangalahy t)
 ; (load-theme 'subdued t)
 ; (load-theme 'inkpot t)
 ; (load-theme 'noctilux t)





  ; http://www.tech-thoughts-blog.com/2013/08/make-emacs-load-random-theme-at-startup.html
  (defun load-random-theme ()
    "Load any random theme from the available ones."
    (interactive)

    ;; disable any previously set theme
    (if (boundp 'theme-of-the-day)
      (progn
        (disable-theme theme-of-the-day)
	    (makunbound 'theme-of-the-day)))
    (defvar themes-list (custom-available-themes))
    (defvar theme-of-the-day (nth (random (length themes-list))
				                  themes-list))
    (load-theme (princ theme-of-the-day) t))

  ; (load-random-theme)

  ; (defvar my/bg-color "#232323")
  ; 背景に合わせる
  (defvar my/bg-color nil)
  (defvar my/fg-color "#333333")
  (set-face-attribute 'whitespace-trailing nil
                      :background my/bg-color
                      :foreground my/fg-color
                      ; :underline t
                      )
  (set-face-attribute 'whitespace-tab nil
                      ; :background my/bg-color
                      :background nil
                      ; :foreground "LightSkyBlue"
                      :foreground my/fg-color
                      ; :underline t
                      )
  (set-face-attribute 'whitespace-space nil
                      :background my/bg-color
                      :foreground my/fg-color
                      ; :weight 'bold
                      )
  (set-face-attribute 'whitespace-empty nil
                      :foreground my/fg-color
                      :background my/bg-color
                      )
  )
; (set-face-background 'show-paren-match (face-background 'default))
(set-face-background 'show-paren-match (face-foreground 'default))
; (set-face-foreground 'show-paren-match "#def")
(set-face-foreground 'show-paren-match (face-background 'default))
; (set-face-attribute 'show-paren-match nil :weight 'bold)

; (set-face-italic-p 'font-lock-comment-face t)

;; for wc mode
;; http://www.emacswiki.org/emacs/WordCountMode
; (require 'wc-mode)
; (wc-mode)

; https://github.com/nishikawasasaki/save-frame-posize.el/blob/master/save-frame-posize.el
(require 'save-frame-posize)

; http://stackoverflow.com/questions/12904043/change-forward-word-backward-word-kill-word-for-camelcase-words-in-emacs
;; M-fとM-bでCamelCase移動。M-left, M-rightには効かない
(global-subword-mode t)

; http://qiita.com/syohex/items/56cf3b7f7d9943f7a7ba
; (require 'anzu)
(global-anzu-mode +1)
(set-face-attribute 'anzu-mode-line nil
					; :foreground "black" :weight 'normal)
					:foreground "RoyalBlue1" :weight 'normal)
; :foreground "selectedKnobColor" :weight 'normal)
; :foreground "snow1" :weight 'normal)
(custom-set-variables
  '(anzu-mode-lighter "")
  '(anzu-deactivate-region t)
  '(anzu-search-threshold 1000)
  '(anzu-replace-to-string-separator " => "))
(global-set-key (kbd "M-%") 'anzu-query-replace)
(global-set-key (kbd "C-M-%") 'anzu-query-replace-regexp)

(global-set-key (kbd "C-c q") 'anzu-query-replace)


;; for tab mode
;; http://ser1zw.hatenablog.com/entry/2012/12/31/022359
;; http://christina04.blog.fc2.com/blog-entry-170.html

(require 'tabbar-ruler)
(setq tabbar-ruler-global-tabbar t) ; If you want tabbar
; (setq tabbar-ruler-global-ruler t) ; if you want a global ruler
(setq tabbar-ruler-popup-menu nil) ; If you want a popup menu.
; (setq tabbar-ruler-popup-toolbar t) ; If you want a popup toolbar
; (setq tabbar-ruler-popup-scrollbar t) ; If you want to only show the
                                      ; scroll bar when your mouse is moving.
; (tabbar-ruler-group-buffer-groups)
; (setq tabbar-buffer-groups-function 'tabbar-buffer-groups)


;; Firefoxライクなキーバインドに
(global-set-key [(control tab)] 'tabbar-forward)
(global-set-key [(control shift tab)] 'tabbar-backward)

(global-set-key [C-right] 'tabbar-forward)
(global-set-key [C-left] 'tabbar-backward)
;; タブ上でマウスホイールを使わない
(tabbar-mwheel-mode nil)
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
;; http://www.emacswiki.org/emacs/TabBarMode
;; *tabbar-display-buffers*以外の*がつくバッファは表示しない
(setq *tabbar-display-buffers* '("*scratch*" "*Messages*" "*grep*" "*Occur*" "*All*" "*helm occur*" "*ag search*"))
(setq tabbar-buffer-list-function
      (lambda ()
        (remove-if
          (lambda(buffer)
            (and (not
                   (loop for name in *tabbar-display-buffers*
                         thereis (string-equal (buffer-name buffer) name))
			       ) (find (aref (buffer-name buffer) 0) " *")))
          (buffer-list))))

; http://cloverrose.hateblo.jp/entry/2013/04/15/183839
;; タブ同士の間隔
(setq tabbar-separator '(0.7))
;; 外観変更
(set-face-attribute
  'tabbar-default nil
  :family (face-attribute 'default :family)
  :background (face-attribute 'mode-line-inactive :background)
  :height 0.8)
(set-face-attribute
  'tabbar-unselected nil
  :background (face-attribute 'mode-line-inactive :background)
  ; :foreground "black"
  :foreground (face-attribute 'mode-line-inactive :foreground)
  :box nil)
(set-face-attribute
  'tabbar-selected nil
  :background (face-attribute 'mode-line :background)
  :foreground (face-attribute 'mode-line :foreground)
  :box nil)


;; https://github.com/m2ym/popwin-el
(require 'popwin)
(popwin-mode 1)
;; Settings for Helm
(setq display-buffer-function 'popwin:display-buffer)
(push '("^\*helm .+\*$" :regexp t) popwin:special-display-config)

(global-set-key (kbd "C-c p") popwin:keymap)

;; ファイラをつける
;; https://github.com/m2ym/direx-el
; (require 'direx)
; (push '(direx:direx-mode :position left :width 25 :dedicated t)
; popwin:special-display-config)
; (global-set-key (kbd "C-c f") 'direx:jump-to-directory-other-window)

;; emacs-nav
; (add-to-list 'load-path "~/.emacs.d/elisp/emacs-nav-49")
(require 'nav)
(global-set-key (kbd "C-c f") 'nav-toggle)

; https://github.com/ancane/emacs-nav
(setq nav-split-window-direction 'vertical) ;; 分割したフレームを垂直に並べる
(defun nav-mode-hl-hook ()
  (local-set-key (kbd "<right>") 'nav-open-file-under-cursor)
  (local-set-key (kbd "<left>")  'nav-go-up-one-dir))

(add-hook 'nav-mode-hook 'nav-mode-hl-hook)


;;; smooth-scroll
; (require 'smooth-scroll)
; (smooth-scroll-mode t)


; {}の中でEnterした場合のみ展開する
(defun expand-bracket ()
  (interactive)
  (if (and (and (< (point-min) (point)) (equal "{" (char-to-string (char-before (point)))))
           (and (< (point) (point-max)) (equal "}" (char-to-string (char-after (point)))))
           )
    (progn
      (newline-and-indent)
      (previous-line)
      (end-of-line)
      (newline-and-indent)
      )
      (newline-and-indent)
    )
  )

; (global-set-key (kbd "C-m") 'expand-bracket)
; (local-set-key (kbd "}") 'check-char-and-insert)
;;for C/C++

; http://www.cozmixng.org/webdav/kensuke/site-lisp/mode/my-c.el
;;; C-mode,C++-modeの設定
(defconst my-c-style
  '(
    ;; 基本オフセット量の設定
    (c-basic-offset             . 2)
    ;; tab キーでインデントを実行
    ; (c-tab-always-indent        . t)
    ;; コメント行のオフセット量の設定
    ; (c-comment-only-line-offset . 0)
    ;; カッコ前後の自動改行処理の設定
    ; (c-hanging-braces-alist
     ; . (
        ; (class-open before after)       ; クラス宣言の'{'の前後
        ; (class-close after)             ; クラス宣言の'}'の後
        ; (defun-open before after)       ; 関数宣言の'{'の前後
        ; (defun-close after)             ; 関数宣言の'}'の後
        ; (inline-open after)             ; クラス内のインライン
                                        ; ; 関数宣言の'{'の後
        ; (inline-close after)            ; クラス内のインライン
                                        ; ; 関数宣言の'}'の後
        ; (brace-list-open after)         ; 列挙型、配列宣言の'{'の後
        ; (brace-list-close before after) ; 列挙型、配列宣言の'}'の前後
        ; (block-open after)              ; ステートメントの'{'の後
        ; (block-close after)             ; ステートメントの'}'前後
        ; (substatement-open after)       ; サブステートメント
                                        ; ; (if 文等)の'{'の後
        ; (statement-case-open after)     ; case 文の'{'の後
        ; (extern-lang-open before after) ; 他言語へのリンケージ宣言の
                                        ; ; '{'の前後
        ; (extern-lang-close before)      ; 他言語へのリンケージ宣言の
                                        ; ; '}'の前
        ; ))
    ;; コロン前後の自動改行処理の設定
    ; (c-hanging-colons-alist
     ; . (
        ; (case-label after)              ; case ラベルの':'の後
        ; (label after)                   ; ラベルの':'の後
        ; (access-label after)            ; アクセスラベル(public等)の':'の後
        ; (member-init-intro)             ; コンストラクタでのメンバー初期化
                                        ; ; リストの先頭の':'では改行しない
        ; (inher-intro before)            ; クラス宣言での継承リストの先頭の
                                        ; ; ':'では改行しない
        ; ))
    ;; 挿入された余計な空白文字のキャンセル条件の設定
    ;; 下記の*を削除する
    ; (c-cleanup-list
     ; . (
	; brace-else-brace                ; else の直前
                                        ; ; "} * else {"  ->  "} else {"
        ; brace-elseif-brace              ; else if の直前
                                        ; ; "} * else if (.*) {"
                                        ; ; ->  } "else if (.*) {"
        ; empty-defun-braces              ; 空のクラス・関数定義の'}' の直前
                                        ; ;；"{ * }"  ->  "{}"
        ; defun-close-semi                ; クラス・関数定義後の';' の直前
                                        ; ; "} * ;"  ->  "};"
        ; list-close-comma                ; 配列初期化時の'},'の直前
                                        ; ; "} * ,"  ->  "},"
        ; scope-operator                  ; スコープ演算子'::' の間
                                        ; ; ": * :"  ->  "::"
        ; ))
    ;; オフセット量の設定
    ;; 必要部分のみ抜粋(他の設定に付いては info 参照)
    ;; オフセット量は下記で指定
    ;; +  c-basic-offsetの 1倍, ++ c-basic-offsetの 2倍
    ;; -  c-basic-offsetの-1倍, -- c-basic-offsetの-2倍
    ; (c-offsets-alist
     ; . (
        ; (arglist-intro          . ++)   ; 引数リストの開始行
        ; (arglist-close          . c-lineup-arglist) ; 引数リストの終了行
        ; (substatement-open      . 0)    ; サブステートメントの開始行
        ; (statement-cont         . ++)   ; ステートメントの継続行
        ; (case-label             . 0)    ; case 文のラベル行
        ; (label                  . 0)    ; ラベル行
        ; (block-open             . 0)    ; ブロックの開始行
        ; (member-init-intro      . ++)   ; メンバオブジェクトの初期化リスト
        ; ))
    ;; インデント時に構文解析情報を表示する
    (c-echo-syntactic-information-p . t)
    )
  "My C Programming Style")

;; hook 用の関数の定義
(defun my-c-mode-common-hook ()
  ;; my-c-stye を登録して有効にする
  (c-add-style "My C Programming Style" my-c-style t)
  ;; 次のスタイルがデフォルトで用意されているので選択してもよい
  ; (c-set-style "gnu")
  ;; (c-set-style "k&r")
  ;; (c-set-style "bsd")
  ;; (c-set-style "linux")
  ;; (c-set-style "cc-mode")
  ;; (c-set-style "stroustrup")
  ;; (c-set-style "ellemtel")
  ;; (c-set-style "whitesmith")
  ;; (c-set-style "python")

  ;; 既存のスタイルを変更する場合は次のようにする
  ;; (c-set-offset 'member-init-intro '++)

  ;; auto-fill-mode を有効にする
  ; (auto-fill-mode t)
  ;; タブ長の設定
  ; (make-variable-buffer-local 'tab-width)
  ; (setq tab-width 2)
  ;; タブの代わりにスペースを使う
  ; (setq indent-tabs-mode nil)
  ;; 自動改行(auto-newline)を有効にする
  ; (setq c-auto-newline t);
  ;; 連続する空白の一括削除(hungry-delete)を有効にする
  (c-toggle-auto-hungry-state t)
  ;; セミコロンで自動改行しない
  (setq c-hanging-semi&comma-criteria nil)

  ;; キーバインドの追加
  ;; ------------------
  ;; C-m        改行＋インデント
  ;; C-c c      コンパイルコマンドの起動
  ;; C-h        空白の一括削除
  ; (define-key c-mode-base-map "\C-m" 'newline-and-indent)
  (define-key c-mode-base-map "\C-cc" 'compile)
  ; (define-key c-mode-base-map "\C-h" 'c-electric-backspace)
  (define-key c-mode-base-map "\C-m" 'expand-bracket)

  ;; コンパイルコマンドの設定
  ;; (setq compile-command "gcc ")
  ; (setq compile-command "make -k ")
  ;; (setq compile-command "gmake -k ")



  ;;HideShow Mode
  (hs-minor-mode)
  (define-key c-mode-base-map (kbd "C-c /") 'hs-toggle-hiding)
    ; (unset-local-key "{")

    (setq flycheck-select-checker
      'c/c++-clang)
    (flycheck-mode)
)

;; for C, C++, Java...
;; モードに入るときに呼び出す hook の設定
(add-hook 'c-mode-common-hook 'my-c-mode-common-hook)


(add-hook 'java-mode-hook (lambda ()
                           (flymake-mode t)
                          ; (flycheck-select-checker 'java-syntax-checker)
                          ; (flycheck-mode)
                          ))


;; for TeX
(add-hook 'tex-mode-hook
          '(lambda ()
			 (local-set-key "\C-j" 'newline-from-anywhere)
       ; (local-set-key (kbd "$") 'skeleton-pair-insert-maybe)
       (modify-syntax-entry ?$ "$" tex-mode-syntax-table)
			 (setq ac-auto-start nil) ;Texモードでは自動補完OFF
			 )
		  )

;; for Lisp
;; (add-hook 'lisp-mode-hook       'hs-minor-mode)

;; for sh
(add-hook 'sh-mode-hook         '(lambda()
                                  (hs-minor-mode)
                                  (local-set-key (kbd "C-c /") 'hs-toggle-hiding)
                                  ))

;;for JavaScript & pegjs

;;js2-mode requires Emacs 24.0 or higher.
(autoload 'js2-mode "js2-mode" nil t)
(defun expand-bracket-for-js2 ()
  (interactive)
  (if (and (and (< (point-min) (point)) (equal "{" (char-to-string (char-before (point)))))
           (and (< (point) (point-max)) (equal "}" (char-to-string (char-after (point)))))
           )
    (progn
      (js2-line-break)
      (previous-line)
      (end-of-line)
      (js2-line-break)
      )
      (js2-line-break)
    )
  )
(defun newline-from-anywhere-for-js2()
  (interactive)
  (end-of-line)
  (js2-line-break) )
(global-set-key (kbd "C-j") 'newline-from-anywhere)
(defun backward-newline-from-anywhere-for-js2()
  (interactive)
  (beginning-of-line)
  (js2-line-break)
  (previous-line)
  (c-indent-command))
(global-set-key (kbd "C-S-j") 'backward-newline-from-anywhere)
(add-to-list 'auto-mode-alist '("\\.\\(peg\\)?js$" . js2-mode))
(add-hook 'js2-mode-hook
          '(lambda ()
             (setq js2-basic-offset 2)
             (define-key js2-mode-map "\C-m" 'expand-bracket-for-js2)
             (define-key js2-mode-map "\C-j" 'newline-from-anywhere-for-js2)
             (define-key js2-mode-map (kbd "C-S-j") 'backward-newline-from-anywhere-for-js2)
             (define-key js2-mode-map (kbd "C-c b") 'web-beautify-js)
             (define-key js2-mode-map (kbd "C-c C-/") 'js2-mode-toggle-element)
             (define-key js2-mode-map (kbd "C-c d") 'js-doc-insert-function-doc)
             (define-key js2-mode-map (kbd "C-c C-d") 'js-doc-insert-file-doc)
             (define-key js2-mode-map (kbd "@") 'js-doc-insert-tag)
             (hs-minor-mode)
             (define-key js2-mode-map (kbd "C-c /") 'hs-toggle-hiding)
             ))

; settings for js-doc
(custom-set-variables
 ; '(js-doc-mail-address "your email address")
 ; '(js-doc-author (format "your name <%s>" js-doc-mail-address))
 ; '(js-doc-url "your url")
 '(js-doc-license "The MIT License")
 )


;;for Haskell
(add-hook 'haskell-mode-hook
          '(lambda ()
            (flycheck-mode)
             ; (local-set-key "\C-c" 'toggle-selective-display)
             ; (turn-on-haskell-simple-indent) ;Simple indentation.
             (turn-on-haskell-indentation) ;Intelligent semi-automatic indentation Mk2.
             (turn-on-haskell-decl-scan) ;Scans top-level declarations, and places them in a menu.
             (turn-on-haskell-doc) ;Echoes types of functions or syntax of keywords when the cursor is idle.
             (define-key haskell-mode-map "\C-j" 'haskell-newline-from-anywhere)
             (define-key haskell-mode-map (kbd "C-S-j") 'haskell-backward-newline-from-anywhere)
             ))
; (add-hook 'haskell-mode-hook 'turn-on-haskell-simple-indent)
(defun haskell-newline-from-anywhere()
  (interactive)
  (end-of-line)
  (haskell-newline-and-indent) )
(defun haskell-backward-newline-from-anywhere()
  (interactive)
  (beginning-of-line)
  (haskell-newline-and-indent)
  (previous-line)
  (indent-for-tab-command))

;; for org
(add-hook 'org-mode-hook
          '(lambda ()
			 (local-set-key "\C-c C-e" 'org-show-block-all)
			 )
		  )

; for grep mode
(add-hook
  'grep-mode-hook
  (lambda ()
		(local-set-key "o" 'next-error-follow-minor-mode)
    ))

(defconst my-codeigniter-style
'(
  ; (c-set-style "ellemtel")
  ;; 基本オフセット量の設定
  (c-basic-offset             . 2)
  ;; tab キーでインデントを実行
  (c-tab-always-indent        . t)
  ;; セミコロンで自動改行しない
  (c-hanging-semi&comma-criteria . nil)
  ; (c-auto-newline . t)

  (indent-tabs-mode . t)
  ;; コメント行のオフセット量の設定
  ; (c-comment-only-line-offset . 0)
  ;
  ;; コメントのスタイル (必要なければコメントアウトする)
  (comment-start . "//")
  (comment-end . "")
  (comment-start-skip . "// *")
  ; http://stackoverflow.com/questions/10758743/how-to-configure-emacs-to-properly-comment-code-in-php-mode
  (comment-use-syntax . t)
   ; (setq comment-start "// "
         ; comment-end   ""
         ; comment-start-skip "// *")


  ;; カッコ前後の自動改行処理の設定
  (c-hanging-braces-alist
   . (
      (class-open before after)       ; クラス宣言の'{'の前後
      (class-close after)             ; クラス宣言の'}'の後
      (defun-open before after)       ; 関数宣言の'{'の前後
      (defun-close after)             ; 関数宣言の'}'の後
      (inline-open after)             ; クラス内のインライン
                                      ; 関数宣言の'{'の後
      (inline-close after)            ; クラス内のインライン
                                      ; 関数宣言の'}'の後
      (brace-list-open after)         ; 列挙型、配列宣言の'{'の後
      (brace-list-close before after) ; 列挙型、配列宣言の'}'の前後
      (block-open before after)              ; ステートメントの'{'の後
      (block-close before after)             ; ステートメントの'}'前後
      (substatement-open before after)       ; サブステートメント
                                      ; (if 文等)の'{'の後
      (statement-case-open after)     ; case 文の'{'の後
      (extern-lang-open before after) ; 他言語へのリンケージ宣言の
                                      ; '{'の前後
      (extern-lang-close before)      ; 他言語へのリンケージ宣言の
                                      ; '}'の前
      ))
  ; コロン前後の自動改行処理の設定
  ; (c-hanging-colons-alist
   ; . (
      ; (case-label after)              ; case ラベルの':'の後
      ; (label after)                   ; ラベルの':'の後
      ; (access-label after)            ; アクセスラベル(public等)の':'の後
      ; (member-init-intro)             ; コンストラクタでのメンバー初期化
                                      ; ; リストの先頭の':'では改行しない
      ; (inher-intro before)            ; クラス宣言での継承リストの先頭の
                                      ; ; ':'では改行しない
      ; {)})

  ; 挿入された余計な空白文字のキャンセル条件の設定
  ; 下記の*を削除する
  ; (c-cleanup-list
   ; . (
; brace-else-brace                ; else の直前
                                      ; ; "} * else {"  ->  "} else {"
      ; brace-elseif-brace              ; else if の直前
                                      ; ; "} * else if (.*) {"
                                      ; ; ->  } "else if (.*) {"
      ; empty-defun-braces              ; 空のクラス・関数定義の'}' の直前
                                      ; ;；"{ * }"  ->  "{}"
      ; defun-close-semi                ; クラス・関数定義後の';' の直前
                                      ; ; "} * ;"  ->  "};"
      ; list-close-comma                ; 配列初期化時の'},'の直前
                                      ; ; "} * ,"  ->  "},"
      ; scope-operator                  ; スコープ演算子'::' の間
                                      ; ; ": * :"  ->  "::"
      ; ))
  ;; オフセット量の設定
  ;; 必要部分のみ抜粋(他の設定に付いては info 参照)
  ;; オフセット量は下記で指定
  ;; +  c-basic-offsetの 1倍, ++ c-basic-offsetの 2倍
  ;; -  c-basic-offsetの-1倍, -- c-basic-offsetの-2倍
  (c-offsets-alist
   . (
      (arglist-intro          . ++)   ; 引数リストの開始行
      (arglist-close          . c-lineup-arglist) ; 引数リストの終了行
      (substatement-open      . 0)    ; サブステートメントの開始行
      (statement-cont         . ++)   ; ステートメントの継続行
      (case-label             . 0)    ; case 文のラベル行
      (label                  . 0)    ; ラベル行
      (block-open             . 0)    ; ブロックの開始行
      (member-init-intro      . ++)   ; メンバオブジェクトの初期化リスト
      ))
  ;; インデント時に構文解析情報を表示する
  (c-echo-syntactic-information-p . t)
  )
"My CodeIgniter Style")

; なぜかphp-mode-hookだと動かなかった・・・
; (add-hook 'php-mode-pear-hook
  ; '(lambda ()
     ; (message "php-mode-pear-hook enabled.")
  ; )
; )

(add-hook 'php-mode-hook
'(lambda ()
   ; (php-enable-psr2-coding-style)
   (c-add-style "My CodeIgniter Style" my-codeigniter-style t)
   ; (c-toggle-auto-hungry-state 1)
   (flymake-mode t)
   (local-set-key (kbd "C-.") 'kill-whole-line)
   (local-set-key (kbd "M-<tab>") 'auto-complete)
   ;配列のインデント修正
   ; http://blog.be-open.net/emacs/php-mode%E9%85%8D%E5%88%97%E3%82%A4%E3%83%B3%E3%83%87%E3%83%B3%E3%83%88/
   (defun ywb-php-lineup-arglist-intro (langelem)
    (save-excursion
     (goto-char (cdr langelem))
     (vector (+ (current-column) c-basic-offset))))
   (defun ywb-php-lineup-arglist-close (langelem)
    (save-excursion
     (goto-char (cdr langelem))
     (vector (current-column))))
   (c-set-offset 'arglist-intro 'ywb-php-lineup-arglist-intro)
   (c-set-offset 'arglist-close 'ywb-php-lineup-arglist-close)
   (remove-hook 'before-save-hook 'delete-trailing-whitespace)
   ; http://qiita.com/itiut@github/items/4d74da2412a29ef59c3a
   (set (make-local-variable 'whitespace-action) nil)
   ; http://www.emacswiki.org/emacs/EmacsSyntaxTable
   (modify-syntax-entry ?$ "." php-mode-syntax-table)
   )
)


(add-hook 'sgml-mode-hook
          '(lambda ()
             (emmet-mode t)
             (flycheck-mode t)
             )
          )

; (require 'generic)
(define-generic-mode my-smarty-mode
  nil
  nil
  ;; 第4引数には，色分けして欲しい単語に当てはまる正規表現と，色分け用の face を書く
  nil
  ;; 第５引数には，brainfuck-mode を有効にするファイルに当てはまる正規表現を書く
  '("\\.tpl\\'")
  ;; 第６引数に，brainfuck-mode の有効時に実行する関数を書く
  ; '(define-bf-keymap bf-help-doc-fun)
  '(web-mode smarty-mode)
  ;; モードの説明
  "Major mode for Smarty")

(add-hook 'smarty-mode-hook
 '(lambda ()
    (setq comment-start "{* "
          comment-end   " *}"
          ; comment-start-skip "{ *"
          comment-multi-line t
          comment-use-syntax t
          indent-tabs-mode t
          c-tab-always-indent t
          )
    (local-set-key (kbd "C-c b") 'web-beautify-html)
    (local-set-key (kbd "C-c /") 'web-mode-fold-or-unfold)
    (local-set-key (kbd "C-c c") 'web-mode-element-close)
    (set (make-local-variable 'whitespace-action) nil)
    (modify-syntax-entry ?$ "." smarty-mode-syntax-table)
    ))

(add-hook 'web-mode-hook
          '(lambda ()
             (emmet-mode t)
             ; (setq indent-tabs-mode t)
             (define-key web-mode-map (kbd "C-c b") 'web-beautify-html)
             (define-key web-mode-map (kbd "C-c /") 'web-mode-fold-or-unfold)
             (define-key web-mode-map (kbd "M-;") nil)
             (define-key web-mode-map (kbd "C-c c") 'web-mode-element-close)
             (setq web-mode-comment-style 2)
             )
          )


(add-hook 'css-mode-hook  'emmet-mode) ;; CSSにも使う

; http://www.haskell.org/haskellwiki/Emacs/Code_folding
;; folding for all rows, starting on the current column
(defun toggle-selective-display (column)
  (interactive "P")
  (set-selective-display
    (or column
        (unless selective-display
          (1+ (current-column))))))

;;for Scala
(add-to-list 'load-path "~/.emacs.d/elisp/scala-mode2")
(require 'scala-mode2)
(add-hook 'scala-mode-hook         '(lambda()
                                      (hs-minor-mode)
                                      (local-set-key (kbd "C-c /") 'hs-toggle-hiding)
                                      ))


;;(autoload 'scala-mode2 "scala-mode2/scala-mode2" nil t)
;;(add-to-list 'auto-mode-alist '("\\.scala$" . scala-mode2))

; http://lists.gnu.org/archive/html/help-gnu-emacs/2005-04/msg00767.html
(defadvice save-place-alist-to-file
           (around save-place-alist-to-file-force-print-length activate)
           (let ((print-level nil)
                 (print-length nil))
             ad-do-it))

;;for vimrc
;;http://stackoverflow.com/questions/4236808/syntax-highlight-a-vimrc-file-in-emacs
(define-generic-mode 'vimrc-generic-mode
                     '("\"")
                     '("if" "endif" "let" "set" "autocmd")
                     '(("^[\t ]*:?\\(!\\|ab\\|map\\|unmap\\)[^\r\n\"]*\"[^\r\n\"]*\\(\"[^\r\n\"]*\"[^\r\n\"]*\\)*$"
                        (0 font-lock-warning-face))
                       ("\\(^\\|[\t ]\\)\\(\".*\\)$"
                        (2 font-lock-comment-face))
                       ("\"\\([^\n\r\"\\]\\|\\.\\)*\""
                        (0 font-lock-string-face)))
                     '("/vimrc\\'" "\\.vim\\(rc\\)?\\'" "\\.gvim\\(rc\\)?\\'")
                     '((lambda ()
                         (modify-syntax-entry ?\" ".")))
                     "Generic mode for Vim configuration files.") ;"
;; for CSS
(add-hook 'css-mode-hook
          '(lambda ()
             (local-set-key "\C-m" 'expand-bracket)
             )
		  )


;; bookmark like Visual Studio
;; http://www.emacswiki.org/emacs/VisibleBookmarks
;; Visual Studioみたいにf2を使う
; (require 'bm)
(global-set-key (kbd "<C-f2>") 'bm-toggle)
(global-set-key (kbd "<f2>")   'bm-next)
(global-set-key (kbd "<S-f2>") 'bm-previous)
(global-set-key (kbd "<M-f2>") 'bm-show-all)
; http://yasuwagon.blogspot.jp/2011/09/bmel.html
; (set-face-background 'bm-face "LightGreen")
; (set-face-background 'bm-fringe-face "LightGreen")
; http://emacsworld.blogspot.jp/2008/09/visual-bookmarks-package-for-emacs.html
(setq bm-highlight-style 'bm-highlight-only-fringe)

;; http://d.hatena.ne.jp/supermassiveblackhole/20100705/1278320568
;; auto-complete
;; 補完候補を自動ポップアップ
(ac-config-default)
(setq ac-auto-start 3)                         ; 4 文字以上で起動
(setq ac-auto-show-menu 0.8)                   ; 0.8秒でメニュー表示
; (setq ac-use-comphist t)                       ; 補完候補をソート
(setq ac-candidate-limit nil)                  ; 補完候補表示を無制限に
(setq ac-use-quick-help nil)                   ; tool tip 無し
(setq ac-use-menu-map t)                       ; キーバインド
(define-key ac-mode-map (kbd "M-<tab>") 'auto-complete)
(define-key ac-menu-map (kbd "C-n")         'ac-next)
(define-key ac-menu-map (kbd "C-p")         'ac-previous)
(setf (symbol-function 'yas-active-keys)
      (lambda ()
        (remove-duplicates
         (mapcan #'yas--table-all-keys (yas--get-snippet-tables)))))
; http://d.hatena.ne.jp/IMAKADO/20090813/1250130343
(defadvice ac-candidate-words-in-buffer (after remove-word-contain-japanese activate)
           (let ((contain-japanese (lambda (s) (string-match (rx (category japanese)) s))))
             (setq ad-return-value
                   (remove-if contain-japanese ad-return-value))))
; http://stackoverflow.com/questions/8095715/emacs-auto-complete-mode-at-startup
(defun auto-complete-mode-maybe ()
  "No maybe for you. Only AC!"
  (unless (minibufferp (current-buffer))
    (auto-complete-mode 1)))
; (global-auto-complete-mode t)
;;(require 'auto-complete-config nil t)
;; (setq ac-dictionary-directories "~/.emacs.d/elisp/ac-dict") ;; 辞書ファイルのディレクトリ
(ac-set-trigger-key "TAB")
; たまに終了できないので切る
(setq ac-use-comphist nil)

;; http://emacs.tsutomuonoda.com/emacs-anything-el-helm-mode-install/
;; for Helm(Anything)
; (add-to-list 'load-path "~/.emacs.d/elisp/helm")
(require 'helm-config)
;; コマンド補完
(helm-mode 1)
;; 自動補完を無効にする
; (setq helm-ff-auto-update-initial-value nil)
; http://www49.atwiki.jp/ntemacs/m/pages/32.html
;; キーバインドを設定する。コマンド起動後は、以下のキーが利用可能となる
;;  ・M-n     ：カーソル位置の単語を検索パターンに追加
;;  ・C-z     ：チラ見
;;  ・C-c C-f ：helm-follow-mode の ON/OFF
(global-set-key (kbd "C-x C-b") 'helm-for-files)
; (define-key helm-command-map (kbd "C-;") 'helm-resume)
; (define-key helm-command-map (kbd "y")   'helm-show-kill-ring)
; (define-key helm-command-map (kbd "o")   'helm-occur)
; (define-key helm-command-map (kbd "C-s") 'helm-occur-from-isearch)
; (define-key helm-command-map (kbd "g")   'helm-do-grep) ; C-u 付で起動すると、recursive となる
; (define-key helm-command-map (kbd "t")   'helm-gtags-find-tag)
(global-set-key (kbd "C-c x") 'helm-mini)
; find-file-at-pointよりもfind^file
; (global-set-key (kbd "C-x C-f") 'find-file)
(global-set-key (kbd "C-x C-f") 'helm-find-files)
;; 候補を作って描写するまでのタイムラグを設定する（デフォルトは 0.1）
(setq helm-idle-delay 0.2)
;; TAB で補完する
(define-key helm-read-file-map (kbd "<tab>") 'helm-execute-persistent-action)
(define-key helm-find-files-map (kbd "<tab>") 'helm-execute-persistent-action)
;; 文字列を入力してから検索するまでのタイムラグを設定する（デフォルトは 0.1）
(setq helm-input-idle-delay 0.2)
;; ミニバッファで C-k 入力時にカーソル以降を削除する（C-u C-k でも同様の動きをする）
(setq helm-delete-minibuffer-contents-from-point t)
;(helm-dired-bindings 1)
; http://hitode909.hatenablog.com/entry/2013/08/04/114845
; (setq helm-ff-transformer-show-only-basename nil)
; http://qiita.com/akisute3@github/items/7c8ea3970e4cbb7baa97
;;; 処理を変更したいコマンドをリストに登録していく
; (add-to-list 'helm-completing-read-handlers-alist '(find-file . nil))

;; Ace-Jump(vim's EasyMotion)
;; https://github.com/winterTTr/ace-jump-mode

;; you can select the key you prefer to
(define-key global-map (kbd "C-c ;") 'ace-jump-mode)
(setq ace-jump-mode-case-fold t) ; case insensitive

; Settings for multiple cursors
; http://qiita.com/ongaeshi/items/3521b814aa4bf162181d
; (add-to-list 'load-path "~/.emacs.d/elisp/multiple-cursors")
(require 'multiple-cursors)
(multiple-cursors-mode)

(require 'smartrep)
(declare-function smartrep-define-key "smartrep")

; (global-set-key (kbd "C-M-c") 'mc/edit-lines)
; (global-set-key (kbd "C-M-r") 'mc/mark-all-in-region)

(global-unset-key "\C-c n")

(smartrep-define-key global-map "C-c n"
	                 '(("C-t"      . 'mc/mark-next-like-this)
		               ("n"        . 'mc/mark-next-like-this)
		               ("p"        . 'mc/mark-previous-like-this)
		               ("m"        . 'mc/mark-more-like-this-extended)
		               ("u"        . 'mc/unmark-next-like-this)
		               ("U"        . 'mc/unmark-previous-like-this)
		               ("s"        . 'mc/skip-to-next-like-this)
		               ("S"        . 'mc/skip-to-previous-like-this)
		               ("*"        . 'mc/mark-all-like-this)
		               ("d"        . 'mc/mark-all-like-this-dwim)
		               ("i"        . 'mc/insert-numbers)
		               ("o"        . 'mc/sort-regions)
		               ("O"        . 'mc/reverse-regions)))

(defun flycheck-display-error-messages (errors)
  (message errors))
(eval-after-load 'flycheck
'(custom-set-variables
 ; '(flycheck-display-errors-function #'flycheck-pos-tip-error-messages)
; ; '(flycheck-add-next-checker
                          ; ; 'javascript-jshint
                         ; ; 'javascript-gjslint
                         '(flycheck-display-errors-delay 0.2)
                         '(flycheck-idle-change-delay
                                 (if flycheck-current-errors 0.5 30.0))
                         '(flycheck-check-syntax-automatically '(save
                                                                 idle-change
                                                                 mode-enabled))
                         ; '(flycheck-display-errors-function #'flycheck-display-error-messages)

                         )
)

; (add-hook 'after-init-hook #'global-flycheck-mode)


; http://qiita.com/akisute3@github/items/6fb94c30f92dae2a24ee
; (flycheck-define-checker c/c++
  ; "A C/C++ checker using g++."
  ; :command ("g++" "-Wall" "-Wextra" source)
  ; :error-patterns  ((error line-start
                           ; (file-name) ":" line ":" column ":" " エラー: " (message)
                           ; line-end)
                    ; (warning line-start
                           ; (file-name) ":" line ":" column ":" " 警告: " (message)
                           ; line-end))
  ; :modes (c-mode c++-mode))

;; http://shnya.jp/blog/?p=477
;; http://emacswiki.org/cgi-bin/emacs/FlyMake
;; flymakeパッケージを読み込み
(require 'flymake)
;; 全てのファイルでflymakeを有効化
;;(add-hook 'find-file-hook 'flymake-find-file-hook)

;; jump to next error
;; http://www.emacswiki.org/emacs/FlyMake
(defun my-flymake-show-next-error()
  (interactive)
  (flymake-goto-next-error)
  (flymake-display-err-menu-for-current-line)
  )
(global-set-key (kbd "C-S-n") 'my-flymake-show-next-error)
(global-set-key (kbd "C-c C-e") 'my-flymake-show-next-error)

(defun my-flymake-show-prev-error()
  (interactive)
  (flymake-goto-prev-error)
  (flymake-display-err-menu-for-current-line)
  )
(global-set-key (kbd "C-S-p") 'my-flymake-show-prev-error)

;; http://www.gnu.org/software/emacs/manual/html_mono/flymake.html
;; http://www.emacswiki.org/emacs/FlyMake
(custom-set-faces
  '(flymake-errline ((((class color)) (:underline "red"))))
  '(flymake-warnline ((((class color)) (:underline "blue")))))

(setq flymake-no-changes-timeout 30)
(setq flymake-start-syntax-check-on-newline nil)
(setq flymake-compilation-prevents-syntax-check t)

;;for C++, C
; C++モードでは flymakeを有効にする
; (add-hook 'c++-mode-hook
          ; '(lambda ()
             ; (flymake-mode t)))

;; Makefile が無くてもC/C++のチェック
; (defun flymake-simple-generic-init (cmd &optional opts)
  ; (let* ((temp-file  (flymake-init-create-temp-buffer-copy
                       ; 'flymake-create-temp-inplace))
         ; (local-file (file-relative-name
                       ; temp-file
                       ; (file-name-directory buffer-file-name))))
    ; (list cmd (append opts (list local-file)))))

; (defun flymake-simple-make-or-generic-init (cmd &optional opts)
  ; (if (file-exists-p "Makefile")
    ; (flymake-simple-make-init)
    ; (flymake-simple-generic-init cmd opts)))

; (defun flymake-c-init ()
  ; (flymake-simple-make-or-generic-init
    ; "gcc"))
; (defun flymake-cc-init ()
  ; (flymake-simple-make-or-generic-init
    ; "g++"))
; (push '("\\.c\\'" flymake-c-init) flymake-allowed-file-name-masks)
; (push '("\\.\\(cc\\|cpp\\|C\\|CPP\\|hpp\\)\\'" flymake-cc-init)
      ; flymake-allowed-file-name-masks)

;;for Java
;; http://www.info.kochi-tech.ac.jp/y-takata/index.php?%A5%E1%A5%F3%A5%D0%A1%BC%2Fy-takata%2FFlymake
(defun flymake-java-init ()
  (flymake-simple-make-init-impl
    'flymake-create-temp-with-folder-structure nil nil
    buffer-file-name
    'flymake-get-java-cmdline))
(defun flymake-get-java-cmdline (source base-dir)
  (list "javac" (list "-J-Dfile.encoding=utf-8" "-encoding" "utf-8"
            source)))
(push '("\\.java$" flymake-java-init) flymake-allowed-file-name-masks)

; http://mugijiru.seesaa.net/article/326967860.html
(defun flymake-php-init ()
  (let* ((temp-file (flymake-init-create-temp-buffer-copy
                     'flymake-create-temp-inplace))
         (local-file (file-relative-name
                      temp-file
                      (file-name-directory buffer-file-name))))
    (list "php" (list "-l" local-file))))
(push '(".+\\.php$" flymake-php-init) flymake-allowed-file-name-masks)
(push '("(Parse|Fatal) error: (.*) in (.*) on line ([0-9]+)" 3 4 nil 2) flymake-err-line-patterns)


; http://d.hatena.ne.jp/CortYuming/20121226/p1
;; クラッシュするキーバインドを無効に
;; パッチを当てたhomebrew版なら大丈夫
; http://blog.n-z.jp/blog/2013-11-12-cocoa-emacs-ime.html
; (global-set-key (kbd "s-p") nil) ; ns-print-buffer
; (global-set-key (kbd "s-S") nil) ; ns-write-file-using-panel
; (global-set-key (kbd "s-o") nil) ; ns-open-file-using-panel
(setq flymake-gui-warnings-enabled nil)

; http://stackoverflow.com/questions/2571436/emacs-annoying-flymake-dialog-box
;; Overwrite flymake-display-warning so that no annoying dialog box is
;; used.
;; This version uses lwarn instead of message-box in the original version.
;; lwarn will open another window, and display the warning in there.
; (defun flymake-display-warning (warning)
  ; "Display a warning to the user, using lwarn"
  ; (lwarn 'flymake :warning warning))
; Using lwarn might be kind of annoying on its own, popping up windows and
; what not. If you prefer to recieve the warnings in the mini-buffer, use:
(defun flymake-display-warning (warning)
  "Display a warning to the user, using lwarn"
  (message warning))

; for rotate text
; http://lists.gnu.org/archive/html/gnu-emacs-sources/2009-04/msg00017.html
(require 'rotate-text)
; (autoload 'rotate-text "rotate-text" nil t)
; (autoload 'rotate-text-backward "rotate-text" nil t)
; (global-set-key "\C-^" 'rotate-text)
; (global-set-key "C-S-^" 'rotate-text-backward)
(define-key global-map (kbd "C-^") 'rotate-text)
(define-key global-map (kbd "C-~") 'rotate-text-backward)
(add-to-list 'rotate-text-symbols '("before" "after"))
(add-to-list 'rotate-text-symbols '("BEFORE" "AFTER"))
(add-to-list 'rotate-text-symbols '("t" "nil"))
(add-to-list 'rotate-text-symbols '("TRUE" "FALSE"))

; http://qiita.com/takc923/items/c3d64b55fc4f3a3b0838
(require 'undo-tree)
(global-set-key (kbd "C-?") 'undo-tree-redo)
(global-set-key (kbd "C-/") 'undo-tree-undo)

; https://github.com/zk-phi/indent-guide
(require 'indent-guide)
(indent-guide-global-mode)
(setq indent-guide-char "¦")

(global-set-key (kbd "C-=") 'er/expand-region)
(global-set-key (kbd "C-M-=") 'contract-region)

(defun contract-region ()
  (interactive)
  (er/expand-region -1))

(global-rainbow-delimiters-mode)

(hlinum-activate)

; http://d.hatena.ne.jp/rubikitch/20081230/pointundo
(require 'point-undo)
; (define-key global-map (kbd "C--") 'point-undo)
; (define-key global-map (kbd "C-+") 'point-redo)
(define-key global-map (kbd "M-[") 'point-undo)
(define-key global-map (kbd "M-]") 'point-redo)

(add-to-list 'load-path "~/.emacs.d/elisp/yasnippet")
(require 'yasnippet)
(setq yas-snippet-dirs
      '(
          "~/.emacs.d/snippets"                 ;; personal snippets
        ; "~/.emacs.d/elisp/some/collection/"           ;; foo-mode and bar-mode snippet collection
        "~/.emacs.d/elisp/yasnippet/yasmate/snippets" ;; the yasmate collection
        "~/.emacs.d/elisp/yasnippet/snippets"         ;; the default collection
        ))
(yas-global-mode 1)  ;; or M-x yas-reload-all if you've started YASnippet already.

(custom-set-variables '(yas-trigger-key "TAB"))

; http://hiroki.jp/2011/01/25/1561/
(require 'auto-highlight-symbol)
(global-auto-highlight-symbol-mode t)
; バッファ全体をハイライトの対象として、変数の一括変更
(custom-set-variables '(ahs-default-range (quote ahs-range-whole-buffer)))

; (require 'wrap-region)

;;; buffer-move
; http://d.hatena.ne.jp/syohex/20130904/1378307029
(global-set-key (kbd "M-g h") 'buf-move-left)
(global-set-key (kbd "M-g j") 'buf-move-down)
(global-set-key (kbd "M-g k") 'buf-move-up)
(global-set-key (kbd "M-g l") 'buf-move-right)


(when (not windows-p)
  (require 'web-mode)
  (add-to-list 'auto-mode-alist '("\\.phtml\\'" . web-mode))
  ; (add-to-list 'auto-mode-alist '("\\.tpl\\.php\\'" . web-mode))
  ; (add-to-list 'auto-mode-alist '("\\.tpl\\'" . web-mode))
  ; (add-to-list 'auto-mode-alist '("\\.php\\'" . web-mode))
  (add-to-list 'auto-mode-alist '("\\.[gj]sp\\'" . web-mode))
  (add-to-list 'auto-mode-alist '("\\.as[cp]x\\'" . web-mode))
  (add-to-list 'auto-mode-alist '("\\.erb\\'" . web-mode))
  (add-to-list 'auto-mode-alist '("\\.mustache\\'" . web-mode))
  (add-to-list 'auto-mode-alist '("\\.djhtml\\'" . web-mode))
  ; (add-to-list 'auto-mode-alist '("\\.html?\\'" . web-mode))
  )



(add-hook 'emmet-mode-hook (lambda ()
                             (setq emmet-indentation 2);; indent はスペース2個
                             ; http://stackoverflow.com/questions/22049702/disabling-preview-for-emmet-mode-in-emacs
                             (setq emmet-preview-default nil)
                             (define-key emmet-mode-keymap (kbd "C-c e") 'emmet-expand-line)
                             (define-key emmet-mode-keymap (kbd "C-j") nil) ;; C-j は newline のままにしておく
                             ))
; (eval-after-load "emmet-mode"
                 ; (lambda ()
                   ; (define-key emmet-mode-keymap (kbd "C-j") nil) ;; C-j は newline のままにしておく
                   ; )
                 ; )

 (require 'sr-speedbar)
; https://gist.github.com/josh/776856
(setq speedbar-frame-parameters
      '((minibuffer)
	(width . 40)
	(border-width . 0)
	(menu-bar-lines . 0)
	(tool-bar-lines . 0)
	(unsplittable . t)
	(left-fringe . 0)))
(setq speedbar-hide-button-brackets-flag t)
(setq speedbar-show-unknown-files t)
(setq speedbar-smart-directory-expand-flag t)
(setq speedbar-use-images nil)
(setq sr-speedbar-auto-refresh t)
(setq sr-speedbar-max-width 50)
(setq sr-speedbar-right-side nil)
(setq sr-speedbar-width-console 40)
(setq speedbar-directory-unshown-regexp "^$")

(make-face 'speedbar-face)
(setq speedbar-mode-hook '(lambda ()
                           (buffer-face-set 'speedbar-face)
                           (define-key speedbar-mode-map "o" 'speedbar-edit-line)
                           (define-key speedbar-mode-map (kbd "<left>") 'speedbar-up-directory)
                           (define-key speedbar-mode-map (kbd "<right>") 'speedbar-edit-line)
                           (define-key speedbar-mode-map (kbd "g") 'grep-find)
                           (define-key speedbar-mode-map (kbd "r") 'speedbar-refresh)
                           (define-key speedbar-mode-map (kbd "f") 'ace-jump-mode)

                           ))

(global-set-key (kbd "C-c s") 'sr-speedbar-toggle)

(when darwin-p
  (when carbon-p
    (set-face-font 'speedbar-face "Inconsolata-11")
    )
  )

(when windows-p
  (set-face-font 'speedbar-face "Meiryo UI-9")
  )

(global-set-key (kbd "C-SPC") 'vim-region-mode)

; (require 'linum-relative)
; ; (autoload 'linum-relative "linum-relative" nil t)
; (global-set-key (kbd "<f4>") 'linum-relative-toggle)
; ; (linum-relative-toggle)

(global-set-key (kbd "C-c m") 'magit-status)

(powerline-default-theme)


(global-set-key (kbd "C-c a") 'all)

;; 適宜keybindの設定
(global-set-key (kbd "<f1>") 'highlight-symbol-at-point)
(global-set-key (kbd "M-<f1>") 'highlight-symbol-remove-all)
; (setq highlight-symbol-colors '("DarkOrange" "DodgerBlue1" "DeepPink1")) ;; 使いたい色を設定、repeatしてくれる

(require 'recentf-ext)
(setq recentf-max-saved-items 100) ; 100個まで履歴として保存
(global-set-key (kbd "C-x o") 'recentf-open-files)
(setq recentf-exclude '(".recentf"))
(setq recentf-auto-cleanup 10)
