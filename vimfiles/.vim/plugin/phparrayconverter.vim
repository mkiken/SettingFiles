" http://blog.starbug1.com/archives/821
function! s:PhpArrayConverter()
	execute "w"
  normal ggdG
  execute "0r!php ~/Desktop/repository/SettingFiles/submodules/php-short-array-syntax-converter/convert.php %"
  normal Gdd
endfunction
command! PhpArrayConverter call <SID>PhpArrayConverter()
