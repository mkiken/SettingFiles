git pull
git submodule sync
git submodule update --recursive
git submodule foreach 'git pull origin master'
