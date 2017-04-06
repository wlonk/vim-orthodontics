" orthodontics.vim - Reshape with braces
" Author:  Kit La Touche <kit@transneptune.net>
" Version: 0.1.0

if !has('pythonx')
    finish
endif

command! OrthoIn call orthodontics#InlineBraces()
command! OrthoOut call orthodontics#OutlineBraces()
command! OrthoToggle call orthodontics#ToggleBraces()
