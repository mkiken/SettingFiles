set noexpandtab

" http://martinlundberg.com/2010/09/29/better-matching-smarty-template-vim/
" Taken form HTML.vim in vim runtime files
if exists("loaded_matchit")
	let b:match_ignorecase = 1
	let b:match_words = '<:>,' .
	\ '<\@<=[ou]l\>[^>]*\%(>\|$\):<\@<=li\>:<\@<=/[ou]l>,' .
	\ '<\@<=dl\>[^>]*\%(>\|$\):<\@<=d[td]\>:<\@<=/dl>,' .
	\ '<\@<=\([^/][^ \t>]*\)[^>]*\%(>\|$\):<\@<=/\1>'
endif
