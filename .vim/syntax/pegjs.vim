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

syn region jsBlock start="{" end="}" contains=ALLBUT,pegOperator,charSet,rule,ruleDef,equals,initialize,exprLabel,literal,innerLiteral,comment,jsBlock

hi def link ruleDef         PreProc
hi def link rule            Type
hi def link exprLabel       Identifier
hi def link literal         String
hi def link pegOperator     Operator
hi def link charSet         Operator
hi def link whitespace      PreProc
hi def link innerLiteral    Comment
"hi def link jsBlock		    Comment
"hi jsBlock guibg=#cccccc
"hi ruleDef gui=underline,bold



" JavaScript Block Syntax(import from javascript.vim)

if !exists("main_syntax")
  if version < 600
    syntax clear
  elseif exists("b:current_syntax")
    finish
  endif
  let main_syntax = 'javascript'
endif

" Drop fold if it set but vim doesn't support it.
if version < 600 && exists("javaScript_fold")
  unlet javaScript_fold
endif


syn keyword javaScriptCommentTodo      TODO FIXME XXX TBD contained
syn match   javaScriptLineComment      "\/\/.*" contains=@Spell,javaScriptCommentTodo contained
syn match   javaScriptCommentSkip      "^[ \t]*\*\($\|[ \t]\+\)" contained

syn region  javaScriptComment	       start="/\*"  end="\*/" contains=@Spell,javaScriptCommentTodo contained
syn match   javaScriptSpecial	       "\\\d\d\d\|\\." contained
syn region  javaScriptStringD	       start=+"+  skip=+\\\\\|\\"+  end=+"\|$+	contains=javaScriptSpecial,@htmlPreproc contained
syn region  javaScriptStringS	       start=+'+  skip=+\\\\\|\\'+  end=+'\|$+	contains=javaScriptSpecial,@htmlPreproc contained

syn match   javaScriptSpecialCharacter "'\\.'" contained
syn match   javaScriptNumber	       "-\=\<\d\+L\=\>\|0[xX][0-9a-fA-F]\+\>"
syn region  javaScriptRegexpString     start=+/[^/*]+me=e-1 skip=+\\\\\|\\/+ end=+/[gi]\{0,2\}\s*$+ end=+/[gi]\{0,2\}\s*[;.,)\]}]+me=e-1 contains=@htmlPreproc oneline contained

syn keyword javaScriptConditional	if else switch
syn keyword javaScriptRepeat		while for do in
syn keyword javaScriptBranch		break continue
syn keyword javaScriptOperator		new delete instanceof typeof
syn keyword javaScriptType		Array Boolean Date Function Number Object String RegExp
syn keyword javaScriptStatement		return with
syn keyword javaScriptBoolean		true false
syn keyword javaScriptNull		null undefined
syn keyword javaScriptIdentifier	arguments this var let
syn keyword javaScriptLabel		case default
syn keyword javaScriptException		try catch finally throw
syn keyword javaScriptMessage		alert confirm prompt status
syn keyword javaScriptGlobal		self window top parent
syn keyword javaScriptMember		document event location
syn keyword javaScriptDeprecated	escape unescape
syn keyword javaScriptReserved		abstract boolean byte char class const debugger double enum export extends final float goto implements import int interface long native package private protected public short static super synchronized throws transient volatile

if exists("javaScript_fold")
    syn match	javaScriptFunction	"\<function\>"
    syn region	javaScriptFunctionFold	start="\<function\>.*[^};]$" end="^\z1}.*$" transparent fold keepend

    syn sync match javaScriptSync	grouphere javaScriptFunctionFold "\<function\>"
    syn sync match javaScriptSync	grouphere NONE "^}"

    setlocal foldmethod=syntax
    setlocal foldtext=getline(v:foldstart)
else
    syn keyword javaScriptFunction	function
    "syn match	javaScriptBraces	   "[{}\[\]]" contained
    syn match	javaScriptBraces	   "[\[\]]" contained
	syn region jsBlocks matchgroup=Function start="{" end="}" contains=ALLBUT,pegOperator,charSet,rule,ruleDef,equals,initialize,exprLabel,literal,innerLiteral,comment,jsBlock containedin=jsBlock,jsBlocks
    syn match	javaScriptParens	   "[()]"
endif


" indent from begenning.
" syn sync fromstart
syn sync maxlines=100

if main_syntax == "javascript"
  syn sync ccomment javaScriptComment
endif

" Define the default highlighting.
" For version 5.7 and earlier: only when not done already
" For version 5.8 and later: only when an item doesn't have highlighting yet
if version >= 508 || !exists("did_javascript_syn_inits")
  if version < 508
    let did_javascript_syn_inits = 1
    command -nargs=+ HiLink hi link <args>
  else
    command -nargs=+ HiLink hi def link <args>
  endif
  HiLink javaScriptComment		Comment
  HiLink javaScriptLineComment		Comment
  HiLink javaScriptCommentTodo		Todo
  HiLink javaScriptSpecial		Special
  HiLink javaScriptStringS		String
  HiLink javaScriptStringD		String
  HiLink javaScriptCharacter		Character
  HiLink javaScriptSpecialCharacter	javaScriptSpecial
  HiLink javaScriptNumber		javaScriptValue
  HiLink javaScriptConditional		Conditional
  HiLink javaScriptRepeat		Repeat
  HiLink javaScriptBranch		Conditional
  HiLink javaScriptOperator		Operator
  HiLink javaScriptType			Type
  HiLink javaScriptStatement		Statement
  HiLink javaScriptFunction		Function
  HiLink javaScriptBraces		Function
  HiLink javaScriptError		Error
  HiLink javaScrParenError		javaScriptError
  HiLink javaScriptNull			Keyword
  HiLink javaScriptBoolean		Boolean
  HiLink javaScriptRegexpString		String
  HiLink javaScriptIdentifier		Identifier
  HiLink javaScriptLabel		Label
  HiLink javaScriptException		Exception
  HiLink javaScriptMessage		Keyword
  HiLink javaScriptGlobal		Keyword
  HiLink javaScriptMember		Keyword
  HiLink javaScriptDeprecated		Exception
  HiLink javaScriptReserved		Keyword
  HiLink javaScriptDebug		Debug
  HiLink javaScriptConstant		Label

  delcommand HiLink
endif

let b:current_syntax = "javascript"
if main_syntax == 'javascript'
  unlet main_syntax
endif



