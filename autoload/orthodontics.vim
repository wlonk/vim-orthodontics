let s:plugin_path = escape(expand('<sfile>:p:h'), '\')
let s:pyfile = escape(s:plugin_path, ' ') . '/orthodontics.py'


function! orthodontics#InlineBraces()
    exe 'pyxfile ' . escape(s:pyfile, ' ')
endfunc

function! orthodontics#OutlineBraces()
    exe 'pyxfile ' . escape(s:pyfile, ' ')
endfunc

function! orthodontics#ToggleBraces()
    exe 'pyxfile ' . escape(s:pyfile, ' ')
endfunc
