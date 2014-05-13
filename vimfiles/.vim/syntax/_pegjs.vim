" Vim syntax file
" Language: PEG JS Grammars
" Maintainer: Kensuke Mori <mkiken0@gmail.com>
" Latest Revision: 15 June 2013
" License: MIT


"This file is pegjs.vim + javascript.vim(vim default).


	" pegjs.vim
	" Language: PEG JS Grammars
	" Maintainer: Andrew Lunny <alunny@gmail.com>
	" Latest Revision: 15 June 2012
	" License: MIT



" PEG's rule Syntax(import from pegjs.vim)

if exists("b:current_syntax")
    finish
endif

syn match pegOperator "[/.+*?&!]"
syn region charSet start="\[" end="\]"
syn match rule "[a-zA-Z$_][a-zA-Z$_0-9]*"
syn match ruleDef "[_a-zA-Z$][a-zA-Z$_0-9]*" contained
syn match equals "=" contained
syn match initialize "[a-zA-Z$_][a-zA-Z$_0-9]*[\n\t ]*\".*\"[\n\t ]*=" contains=ruleDef,equals,innerLiteral
syn match initialize "[a-zA-Z$_][a-zA-Z$_0-9]*[\n\t ]*'.*'[\n\t ]*=" contains=ruleDef,equals,innerLiteral
syn match initialize "[a-zA-Z$_][a-zA-Z$_0-9]*[\n\t ]*=" contains=ruleDef,equals
syn match exprLabel "[a-zA-Z$_][a-zA-Z$_0-9]*:"he=e-1
syn region literal start="'" end="'"
syn region literal start="\"" end="\""
syn region innerLiteral start="'" end="'" contained
syn region innerLiteral start="\"" end="\"" contained
syn region comment start="/[*]" end="[*]/"
syn region comment start="//" end="\n"

" syn region jsBlock start="{" end="}" contains=ALLBUT,pegOperator,charSet,rule,ruleDef,equals,initialize,exprLabel,literal,innerLiteral,comment,jsBlock

hi def link ruleDef         PreProc
hi def link rule            Type
hi def link exprLabel       Identifier
hi def link literal         String
hi def link pegOperator     Operator
hi def link charSet         Operator
hi def link whitespace      PreProc
hi def link innerLiteral    Comment
" hi def link jsBlock		    Comment
hi jsBlock guibg=#cccccc
"hi ruleDef gui=underline,bold


