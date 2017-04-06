" orthodontics.vim - Reshape with braces
" Author:  Kit La Touche <kit@transneptune.net>
" Version: 0.1.0

if !has('python')
    finish
endif


function! InlineBraces()
    pyfile orthodontics.py
endfunc

function! OutlineBraces()
    pyfile orthodontics.py
endfunc

function! ToggleBraces()
    pyfile orthodontics.py
endfunc

command! OrthoIn call orthodontics#InlineBraces()
command! OrthoOut call orthodontics#OutlineBraces()
command! OrthoToggle call orthodontics#ToggleBraces()
