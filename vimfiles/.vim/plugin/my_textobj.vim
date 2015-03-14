if exists('g:loaded_textobj_my_textobj')
  finish
endif

let loaded_textobj_my_textobj = 1

call textobj#user#plugin('sentence', {
\      '-': {
\           'pattern': '[A-Za-z_\-][a-zA-Z0-9_\-]\+',
\           'select': ['as', 'is'],
\      },
\   })


call textobj#user#plugin('variable', {
\      '-': {
\           'pattern': '$[A-Za-z_][a-zA-Z0-9_]\+',
\           'select': ['av', 'iv'],
\      },
\   })


call textobj#user#plugin('newline', {
\      '-': {
\           'pattern': '[\n]\+',
\           'select': ['an', 'in'],
\      },
\   })
