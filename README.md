<!-- サブモジュールのダウンロード -->
git submodule update --init

<!-- シンボリックリンク作成 -->
./dl.sh

<!-- for vim -->
:BundleInstall

<!-- サブモジュールの足し方 -->
git submodule add https://github.com/magnars/multiple-cursors.el.git .emacs.d/elisp/multiple-cursors
