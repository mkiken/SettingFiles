set noexpandtab
nnoremap <Leader>@ /function<space>

function! JumpToDeclaration()
	let tag = tagbar#currenttag('%s', 'No current tag')
	if tag == 'No current tag'
		echo tag
		return
	endif
	exec '?' . tag
endfunction

nmap <silent>  <leader>#  :call JumpToDeclaration()<CR>

nnoremap <leader>" #/function <C-r>/<CR>
