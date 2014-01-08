#!/bin/sh

# Repo="${HOME}/Desktop/repository/SettingFiles/"
Repo="`pwd`/"
# cp .aliases ~/.aliases
# cp .gitconfig ~/.gitconfig
# cp .gitignore ~/.gitignore
# cp .gitmodules ~/.gitmodules
# cp .gvimrc ~/.gvimrc
# cp .vimrc ~/.vimrc
# cp .zshrc ~/.zshrc
# cp .emacs.d/init.el ~/.emacs.d/init.el

echo "ln -si ${Repo}.aliases ~/.aliases"
ln -si "${Repo}.aliases" ~/.aliases

echo "ln -si ${Repo}.gitconfig ~/.gitconfig"
ln -si "${Repo}.gitconfig" ~/.gitconfig

echo "ln -si ${Repo}.gitignore_global ~/.gitignore"
ln -si "${Repo}.gitignore_global" ~/.gitignore

echo "ln -si ${Repo}.gvimrc ~/.gvimrc"
ln -si "${Repo}.gvimrc" ~/.gvimrc

echo "ln -si ${Repo}.vimrc ~/.vimrc"
ln -si "${Repo}.vimrc" ~/.vimrc

echo "ln -si ${Repo}.zshrc ~/.zshrc"
ln -si "${Repo}.zshrc" ~/.zshrc

echo "ln -si ${Repo}.emacs.d ~/.emacs.d"
ln -si "${Repo}.emacs.d" ~/.emacs.d

echo "ln -si ${Repo}.vim ~/.vim"
ln -si "${Repo}.vim" ~/.vim

echo 'copy done.'


# mkdir -p ~/.backup
mkdir -p ~/.backup/emacs/backup
mkdir -p ~/.backup/emacs/autosave
mkdir -p ~/.backup/vim/backup
mkdir -p ~/.backup/vim/swap

echo 'backup directory for emacs and vim made.'

git submodule sync
# http://rochefort.hatenablog.com/entry/20110410/p1
# git submodule foreach 'git pull origin master'
git submodule update --init
echo 'submodule update.'
