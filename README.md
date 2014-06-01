<!-- サブモジュールのダウンロード -->
git submodule update --init --recursive

<!-- シンボリックリンク作成 -->
./dl.sh

<!-- for vim -->
:BundleInstall

<!-- for emacs -->
package-initialize.elをM-x eval-buffer

<!-- サブモジュールの足し方 -->
git submodule add https://github.com/magnars/multiple-cursors.el.git .emacs.d/elisp/multiple-cursors
