#read Aliases
source ~/.aliases

export PATH=/usr/local/bin:$PATH:/usr/local/share/npm/bin
export MANPATH=/usr/local/man:$MANPATH

export PS1="\h:\W \u \t \# \[\e[0;36m\]$\[\e[00m\] "

#You can force Git to ignore these errors by setting GIT_SSL_NO_VERIFY.
export GIT_SSL_NO_VERIFY=1

#for Haskell
#export PATH="~/.cabal/bin:$PATH";

#for Scala
export SCALA_HOME=/usr/local/share/scala-2.9.2
export PATH=$PATH:$SCALA_HOME/bin
