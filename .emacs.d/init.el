;;http://d.hatena.ne.jp/tomoya/20090807/1249601308
;;MacとWindowsで場合分け
(defun x->bool (elt) (not (not elt)))

;; emacs-version predicates
;; (setq emacs22-p (string-match "^22" emacs-version)
;; 	  emacs23-p (string-match "^23" emacs-version)
;; 	  emacs23.0-p (string-match "^23\.0" emacs-version))

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
  (define-key global-map (kbd "s-v") 'my-yank)
  ; http://blog.n-z.jp/blog/2013-11-12-cocoa-emacs-ime.html
  (when (boundp 'mac-input-method-parameters)
    ;; ime inline patch
		(setq default-input-method "MacOSX")
		; (mapc
       ; (lambda (param)
         ; (let ((name (car param)))
           ; (cond
            ; ((string-match "Japanese\\(\\.base\\)?\\'" name) ;; ひらがなの日本語入力
              ; (mac-set-input-method-parameter name 'cursor-color "blue"))
            ; ((string-match "Japanese" name) ;; カナなどの日本語入力
              ; (mac-set-input-method-parameter name 'cursor-color "red"))
            ; ((string-match "Roman" name) ;; 英字
              ; (mac-set-input-method-parameter name 'cursor-color "black"))
            ; (t ;; その他
               ; (mac-set-input-method-parameter name 'cursor-color "yellow"))
            ; )
           ; ))
       ; mac-input-method-parameters)
    ; (mac-set-input-method-parameter "com.apple.keylayout.US" 'cursor-color "black")
		;; IMの状態で色を分ける
		(mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Roman" 'cursor-color "blue")     ; ことえり ローマ字
		; (mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Roman" 'title "A")     ; ことえり ローマ字
		(mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Japanese" 'cursor-color "magenta") ; ことえり 日本語
		(mac-set-input-method-parameter "com.apple.inputmethod.Kotoeri.Japanese.Katakana" 'cursor-color "yellow") ; ことえり 日本語
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
  ;; Window間の移動をM-...でやる
  ;; http://www.emacswiki.org/emacs/WindMove
  ; (windmove-default-keybindings 'super)
  ;; (global-set-key (kbd "M-<left>")  'windmove-left)

  ;; font settings
  (when (>= emacs-major-version 23)
	(setq fixed-width-use-QuickDraw-for-ascii t)
	(setq mac-allow-anti-aliasing t)
	(set-face-attribute 'default nil
						:family "monaco"
						:height 125)
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
			("-cdac$" . 1.2))))
  )


;; Settings for Windows
(when windows-p
  (set-face-font 'default "Meiryo UI-13")
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

;; カーソルの場所を保存する
(require 'saveplace)
(setq-default save-place t)
(show-paren-mode 1)
(setq show-paren-delay 0)
(setq show-paren-style 'expression)

; http://qiita.com/catatsuy/items/55d50d13ebc965e5f31e
(require 'uniquify)
(setq uniquify-buffer-name-style 'post-forward)

;; バックアップファイルを作らない
(setq make-backup-files nil)
(setq auto-save-default nil)

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
  (end-of-visual-line)
  (newline-and-indent) )
(global-set-key (kbd "C-j") 'newline-from-anywhere)


	(global-set-key (kbd "C-<left>")  'windmove-left)
	(global-set-key (kbd "C-<left>")  'windmove-left)
	(global-set-key (kbd "C-<left>")  'windmove-left)
	(global-set-key (kbd "C-<left>")  'windmove-left)

;; http://dev.ariel-networks.com/wp/documents/aritcles/emacs/part16
;;範囲指定していないとき、C-wで前の単語を削除
(defadvice kill-region (around kill-word-or-kill-region activate)
  (if (and (interactive-p) transient-mark-mode (not mark-active))
      (backward-kill-word 1)
    ad-do-it))
;; minibuffer用
(define-key minibuffer-local-completion-map "\C-w" 'backward-kill-word)
;; カーソル位置の単語を削除
(defun kill-word-at-point ()
  (interactive)
  (let ((char (char-to-string (char-after (point)))))
    (cond
     ((string= " " char) (delete-horizontal-space))
     ((string-match "[\t\n -@\[-`{-~]" char) (kill-word 1))
     (t (forward-char) (backward-word) (kill-word 1)))))
(global-set-key "\M-d" 'kill-word-at-point)

;; kill-lineで行が連結したときにインデントを減らす
(defadvice kill-line (before kill-line-and-fixup activate)
  (when (and (not (bolp)) (eolp))
    (forward-char)
    (fixup-whitespace)
    (backward-char)))

;; M-dで単語のどこからでも削除できるようにする
;(defun kill-word-from-anywhere()
;  (interactive)
;  (forward-char)
;  (backward-word)
;  (kill-word 1) )
;(global-set-key (kbd "M-d") 'kill-word-from-anywhere)

;; ペースト後に整形
(defun my-yank()
  (interactive)
  (yank)
  (backward-char)
  (indent-for-tab-command)
  (forward-char)
  )

;;インデントはタブにする
(setq indent-tabs-mode t)
;; tab ではなく space を使う
										;(setq-default indent-tabs-mode nil)
;;タブ幅
(setq-default tab-width 4)
(setq default-tab-width 4)
(setq tab-stop-list '(4 8 12 16 20 24 28 32 36 40 44 48 52 56 60
						64 68 72 76 80 84 88 92 96 100 104 108 112 116 120))
;; http://reiare.net/blog/2010/12/16/emacs-space-tab/
;; 最後に改行を入れる。
(setq require-final-newline t)

;; 行末の空白を表示
;;(setq-default show-trailing-whitespace t)


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

(setq whitespace-display-mappings
      '((space-mark ?\u3000 [?\u25a1])
        ;; WARNING: the mapping below has a problem.
        ;; When a TAB occupies exactly one column, it will display the
        ;; character ?\xBB at that column followed by a TAB which goes to
        ;; the next TAB column.
        ;; If this is a problem for you, please, comment the line below.
        (tab-mark ?\t [?\u00BB ?\t] [?\\ ?\t])))

;; スペースは全角のみを可視化
(setq whitespace-space-regexp "\\(\u3000+\\)")

;; 保存前に自動でクリーンアップ
(setq whitespace-action '(auto-cleanup))

(global-whitespace-mode 1)

(defvar my/bg-color "#232323")
(set-face-attribute 'whitespace-trailing nil
                    :background my/bg-color
                    :foreground "DeepPink"
                    :underline t)
(set-face-attribute 'whitespace-tab nil
                    :background my/bg-color
                    :foreground "LightSkyBlue"
                    :underline t)
(set-face-attribute 'whitespace-space nil
                    :background my/bg-color
                    :foreground "GreenYellow"
                    :weight 'bold)
(set-face-attribute 'whitespace-empty nil
                    :background my/bg-color)


;;保存時に行末の空白を全て削除
;;from http://d.hatena.ne.jp/tototoshi/20101202/1291289625
(add-hook 'before-save-hook 'delete-trailing-whitespace)

;;http://masutaka.net/chalow/2011-10-12-1.html
;;(global-whitespace-mode 1)

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

(global-set-key (kbd "C-,") 'copy-oneline)
(global-set-key (kbd "C-.") 'kill-whole-line)

;; viのpのように改行してヤンク
(defun vi-p ()
  (interactive)
  (end-of-visual-line)
  (newline-and-indent)
  (my-yank)
  ; (delete-backward-char 1)
  ; (previous-line)
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


;;http://flex.ee.uec.ac.jp/texi/faq-jp/faq-jp_130.html
;; By an unknown contributor
(defun match-paren (arg)
  "Go to the matching parenthesis if on parenthesis otherwise insert %."
  (interactive "p")
  (cond ((looking-at "\\s\(") (forward-list 1) (backward-char 1))
		((looking-at "\\s\)") (forward-char 1) (backward-list 1))
		(t (self-insert-command (or arg 1)))))
(global-set-key (kbd "C-]") 'match-paren)

;; 対応するカッコまでをコピー
;; http://d.hatena.ne.jp/takehikom/20121120/1353358800
(defun match-paren-kill-ring-save ()
  "Copy region from here to the matching parenthesis to kill ring and save."
  (interactive)
  (set-mark-command nil)
  (match-paren-japanese nil)
  (forward-char)
  (exchange-point-and-mark)
  (clipboard-kill-ring-save (mark) (point))
  (let ((c (abs (- (mark) (point)))))
    (message "match-paren-kill-ring-save: %d characters saved" c)))
(global-set-key (kbd "C-M-]") 'match-paren-kill-ring-save)

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

; http://metalphaeton.blogspot.jp/2011/04/emacs.html
(global-set-key (kbd "(") 'skeleton-pair-insert-maybe)
(global-set-key (kbd "{") 'skeleton-pair-insert-maybe)
(global-set-key (kbd "[") 'skeleton-pair-insert-maybe)
(global-set-key (kbd "\"") 'skeleton-pair-insert-maybe)
(setq skeleton-pair 1)


;起動時のフレームサイズを設定する
(setq initial-frame-alist
			(append (list
;        '(width . 130)
;        '(height . 35)
		'(alpha . (98 95)) ;; 透明度。(アクティブ時, 非アクティブ時)
				)
				initial-frame-alist))
(setq default-frame-alist initial-frame-alist)

;;http://www.bookshelf.jp/soft/meadow_23.html#SEC231
;; ファイルやURLをクリック出来るようにする
(ffap-bindings)

;; ツールバーを非表示
;; M-x tool-bar-mode で表示非表示を切り替えられる
(tool-bar-mode -1)

;; 矩形選択
;; http://dev.ariel-networks.com/articles/emacs/part5/
(cua-mode t)
(setq cua-enable-cua-keys nil)

;;; ediffを1ウィンドウで実行
(setq ediff-window-setup-function 'ediff-setup-windows-plain)


;; server start for emacs-client
;; http://d.hatena.ne.jp/syohex/20101224/1293206906
(require 'server)
(unless (server-running-p)
  (server-start))


;;import
(add-to-list 'load-path "~/.emacs.d/elisp")

;; Color Scheme
(add-to-list 'custom-theme-load-path "~/.emacs.d/themes")
(load-theme 'my-monokai t)
;; (load-theme 'monokai t)
;; (load-theme 'molokai t)
;; (load-theme 'monokai-dark-soda t)
;; (load-theme 'zenburn t)
;; (load-theme 'solarized-light t)
;; (load-theme 'solarized-dark t)
;; (load-theme 'twilight-anti-bright t)
;; (load-theme 'tomorrow-night-paradise t)
;; (load-theme 'tomorrow-night-blue t)
;; (load-theme 'tomorrow-night-bright t)
;; (load-theme 'tomorrow-night-eighties t)
;; (load-theme 'tomorrow-night t)
;; (load-theme 'tomorrow t)
;; (load-theme 'twilight-bright t)

;; for wc mode
;; http://www.emacswiki.org/emacs/WordCountMode
(require 'wc-mode)

; https://github.com/nishikawasasaki/save-frame-posize.el/blob/master/save-frame-posize.el
(require 'save-frame-posize)

; http://stackoverflow.com/questions/12904043/change-forward-word-backward-word-kill-word-for-camelcase-words-in-emacs
;; M-fとM-dでCamelCase移動。M-left, M-rightには効かない
(global-subword-mode t)

	; http://qiita.com/syohex/items/56cf3b7f7d9943f7a7ba
(require 'anzu)
(global-anzu-mode +1)
(set-face-attribute 'anzu-mode-line nil
                    :foreground "Blue" :weight 'normal)
(global-set-key (kbd "M-%") 'anzu-query-replace)
(global-set-key (kbd "C-M-%") 'anzu-query-replace-regexp)

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
(setq *tabbar-display-buffers* '("*scratch*" "*Messages*"))
(setq tabbar-buffer-list-function
       (lambda ()
         (remove-if
          (lambda(buffer)
            (and (not
                (loop for name in *tabbar-display-buffers*
                       thereis (string-equal (buffer-name buffer) name))
			) (find (aref (buffer-name buffer) 0) " *")))
          (buffer-list))))

;; タブ同士の間隔
;; http://cloverrose.hateblo.jp/entry/2013/04/15/183839
(setq tabbar-separator '(0.7))
;; 外観変更
(set-face-attribute
 'tabbar-default nil
 :family (face-attribute 'default :family)
 :background (face-attribute 'mode-line-inactive :background)
 :height 0.9)
(set-face-attribute
 'tabbar-unselected nil
 :background (face-attribute 'mode-line-inactive :background)
 :foreground "black" ;; (face-attribute 'mode-line-inactive :foreground)
 :box nil)
(set-face-attribute
 'tabbar-selected nil
 :background (face-attribute 'mode-line :background)
 :foreground (face-attribute 'mode-line :foreground)
 :box nil)


;; HideShow Mode
;; http://www.emacswiki.org/emacs/HideShow
(define-key global-map (kbd "C-c /") 'hs-toggle-hiding)

;; https://github.com/m2ym/popwin-el
(require 'popwin)
(popwin-mode 1)
;; Settings for Helm
(setq display-buffer-function 'popwin:display-buffer)
(push '("^\*helm .+\*$" :regexp t) popwin:special-display-config)

;; ファイラをつける
;; https://github.com/m2ym/direx-el
; (require 'direx)
; (push '(direx:direx-mode :position left :width 25 :dedicated t)
      ; popwin:special-display-config)
; (global-set-key (kbd "C-c f") 'direx:jump-to-directory-other-window)

;; emacs-nav
(add-to-list 'load-path "~/.emacs.d/elisp/emacs-nav-49")
(require 'nav)
(global-set-key (kbd "C-c f") 'nav-toggle) ;; C-x C-d で nav をトグル
(setq nav-split-window-direction 'vertical) ;; 分割したフレームを垂直に並べる

;;; smooth-scroll
(require 'smooth-scroll)
(smooth-scroll-mode t)



;;for C/C++
(add-hook 'c-mode-common-hook   'hs-minor-mode)

;; for Java
(add-hook 'java-mode-hook       'hs-minor-mode)

;; for TeX
(add-hook 'tex-mode-hook
          '(lambda ()
			 (local-set-key "\C-j" 'newline-from-anywhere)))

;; for Lisp
;; (add-hook 'lisp-mode-hook       'hs-minor-mode)

;; for sh
(add-hook 'sh-mode-hook         'hs-minor-mode)

;;for JavaScript & pegjs
;;js2-mode requires Emacs 24.0 or higher.
(autoload 'js2-mode "js2-mode" nil t)
(add-to-list 'auto-mode-alist '("\\.\\(peg\\)?js$" . js2-mode))
(add-hook 'js2-mode-hook
          '(lambda ()
			 (local-set-key "\C-c/" 'js2-mode-toggle-element)))

;;for Haskell
(autoload 'haskell-mode "haskell-mode-2.8.0/haskell-mode" nil t)
(add-to-list 'auto-mode-alist '("\\.hs$" . haskell-mode))
(add-hook 'haskell-mode-hook
          '(lambda ()
			 (local-set-key "\C-c/" 'toggle-selective-display)))

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
(add-hook 'scala-mode-hook         'hs-minor-mode)
;;(autoload 'scala-mode2 "scala-mode2/scala-mode2" nil t)
;;(add-to-list 'auto-mode-alist '("\\.scala$" . scala-mode2))

;;for MiniMap(Sublime Text)
;; from http://www.emacswiki.org/emacs/MiniMap
(require 'minimap)
(global-set-key "\C-cm" 'minimap-create)
(global-set-key "\C-c\M-m" 'minimap-kill)

;; bookmark like Visual Studio
;; http://www.emacswiki.org/emacs/VisibleBookmarks
;; Visual Studioみたいにf2を使う
(require 'bm)
(global-set-key (kbd "<C-f2>") 'bm-toggle)
(global-set-key (kbd "<f2>")   'bm-next)
(global-set-key (kbd "<S-f2>") 'bm-previous)

;; for auto-install
;; http://d.hatena.ne.jp/rubikitch/20091221/autoinstall
;; 実行時だけ有効にする
; (require 'auto-install)
; (setq auto-install-directory "~/.emacs.d/elisp/temp")
; (auto-install-update-emacswiki-package-name t)
; (auto-install-compatibility-setup)             ; 互換性確保


; for package.el
; Emacs24
; http://ongaeshi.hatenablog.com/entry/20120613/1339607400
;; 実行時だけ有効にする
; (progn
  ; (switch-to-buffer
   ; (url-retrieve-synchronously
    ; "https://raw.github.com/milkypostman/melpa/master/melpa.el"))
  ; (package-install-from-buffer  (package-buffer-info) 'single))
; (require 'package)
; ; Add package-archives
; (add-to-list 'package-archives '("melpa" . "http://melpa.milkbox.net/packages/") t)
; (add-to-list 'package-archives '("marmalade" . "http://marmalade-repo.org/packages/"))
; ; Initialize
; (package-initialize)
; ; melpa.el
; (require 'melpa)

;; http://d.hatena.ne.jp/supermassiveblackhole/20100705/1278320568
;; auto-complete
;; 補完候補を自動ポップアップ
(add-to-list 'load-path "~/.emacs.d/elisp/auto-complete")
; ;;(add-to-list 'ac-dictionary-directories "~/.emacs.d/ac-dict")
(require 'auto-complete-config)
(ac-config-default)
(define-key ac-mode-map (kbd "M-TAB") 'auto-complete)
; ;;(require 'auto-complete)
; (global-auto-complete-mode t)
;;(require 'auto-complete-config nil t)
;; (setq ac-dictionary-directories "~/.emacs.d/elisp/ac-dict") ;; 辞書ファイルのディレクトリ
(ac-set-trigger-key "TAB")
;; for c/c++
;; http://cx4a.org/software/auto-complete/manual.html
;; (add-hook 'c++-mode (lambda () (add-to-list 'ac-sources 'ac-source-semantic)))
; (icomplete-mode 1)

;; http://emacs.tsutomuonoda.com/emacs-anything-el-helm-mode-install/
;; for Helm(Anything)
(add-to-list 'load-path "~/.emacs.d/elisp/helm")
(require 'helm-config)
(global-set-key (kbd "C-c h") 'helm-mini)
;; コマンド補完
(helm-mode 1)
;(helm-dired-bindings 1)

;; Ace-Jump(vim's EasyMotion)
;; https://github.com/winterTTr/ace-jump-mode
(autoload
  'ace-jump-mode
  "ace-jump-mode"
  "Emacs quick move minor mode"
  t)
;; you can select the key you prefer to
(define-key global-map (kbd "C-c ;") 'ace-jump-mode)

; Settings for multiple cursors
; http://qiita.com/ongaeshi/items/3521b814aa4bf162181d
(add-to-list 'load-path "~/.emacs.d/elisp/multiple-cursors.el")
(require 'multiple-cursors)
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


;; http://shnya.jp/blog/?p=477
;; http://emacswiki.org/cgi-bin/emacs/FlyMake
;; flymakeパッケージを読み込み
(require 'flymake)
;; 全てのファイルでflymakeを有効化
;;(add-hook 'find-file-hook 'flymake-find-file-hook)

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

(defun my-flymake-show-prev-error()
  (interactive)
  (flymake-goto-prev-error)
  (flymake-display-err-menu-for-current-line)
  )
(global-set-key "\M-p" 'my-flymake-show-prev-error)

;; http://www.gnu.org/software/emacs/manual/html_mono/flymake.html
;; http://www.emacswiki.org/emacs/FlyMake
(custom-set-faces
 '(flymake-errline ((((class color)) (:underline "red"))))
 '(flymake-warnline ((((class color)) (:underline "blue")))))

(setq flymake-no-changes-timeout 5)
;;(setq flymake-start-syntax-check-on-newline nil)
(setq flymake-compilation-prevents-syntax-check t)

;;for C++, C
; C++モードでは flymakeを有効にする
(add-hook 'c++-mode-hook
                  '(lambda ()
                         (flymake-mode t)))

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

;;for Java
;; http://www.info.kochi-tech.ac.jp/y-takata/index.php?%A5%E1%A5%F3%A5%D0%A1%BC%2Fy-takata%2FFlymake
(add-hook 'java-mode-hook 'flymake-mode-on)
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
