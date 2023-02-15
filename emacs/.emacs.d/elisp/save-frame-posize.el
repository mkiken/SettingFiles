;; save-frame-posize.el

;; Copyright (C) 2012 by nishikawasasaki
;; Author: nishikawasasaki
;; https://github.com/nishikawasasaki/save-frame-posize.el


;; This file is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation; either version 2, or (at your option)
;; any later version.

;; This file is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with GNU Emacs; see the file COPYING.  If not, write to the
;; Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
;; Boston, MA 02110-1301, USA.

;; What is this?
;; Save GNU Emacs frame size and position.
;; Restore the size and position when you launch Emacs.


;; Install
;; Move this file into directory in load-path.
;; And this add to init.el
;; (require 'save-frame-posize)

;; ChangeLog
;; see https://github.com/nishikawasasaki/save-frame-posize.el

; arrange with
; http://ck.kennt-wayne.de/2011/jul/emacs-restore-last-frame-size-on-startup

;; var ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defvar sfps-save-file "~/.backup/emacs/.frameposize")
(defvar sfps-delimiter ",")


;; func ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defun save-framegeometry ()
  "Gets the current frame's geometry and saves to sfps-save-file."
  (let (
        (framegeometry-left (frame-parameter (selected-frame) 'left))
        (framegeometry-top (frame-parameter (selected-frame) 'top))
        (framegeometry-width (frame-parameter (selected-frame) 'width))
        (framegeometry-height (frame-parameter (selected-frame) 'height))
        (framegeometry-file (expand-file-name sfps-save-file))
        )

    (with-temp-buffer
      (insert
       ";;; This is the previous emacs frame's geometry.\n"
       ";;; Last generated " (current-time-string) ".\n"
       "(setq initial-frame-alist\n"
       "      '(\n"
       (format "        (top . %d)\n" (max framegeometry-top 0))
       (format "        (left . %d)\n" (max framegeometry-left 0))
       (format "        (width . %d)\n" (max framegeometry-width 0))
       (format "        (height . %d)))\n" (max framegeometry-height 0)))
      (when (file-writable-p framegeometry-file)
        (write-file framegeometry-file))))
  )

(defun load-framegeometry ()
  "Loads sfps-save-file which should load the previous frame's geometry."
  (let ((framegeometry-file (expand-file-name sfps-save-file)))
    (when (file-readable-p framegeometry-file)
      (load-file framegeometry-file)))
  )

;; Special work to do ONLY when there is a window system being used
(if window-system
    (progn
      (add-hook 'after-init-hook 'load-framegeometry)
      (add-hook 'kill-emacs-hook 'save-framegeometry))
  )

;; eof

(provide 'save-frame-posize)
