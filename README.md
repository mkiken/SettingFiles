##初期化
####Mac OS X

    cd mac
    ./initialize

####Windows

PowerShellで

    cd windows
    ./initialize.ps1

##更新
####Mac OS X

    cd mac
    ./update

####Windows

PowerShellで

    cd windows
    ./update.ps1

##エディタプラグインの更新
####Vim
Vimコマンドで

    :BundleInstall

####Emacs
./.emacs.d/package-initialize.elをEmacsで開いて

    M-x eval-buffer

####Sublime Text 2
./SublimeTextFiles/2/initialize.txt


####Atom
./.atom/atom_packages.txt
