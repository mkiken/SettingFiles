# Your init script
#
# Atom will evaluate this file each time a new window is opened. It is run
# after packages are loaded/activated and after the previous editor state
# has been restored.
#
# An example hack to make opened Markdown files always be soft wrapped:
#
# path = require 'path'
#
# atom.workspaceView.eachEditorView (editorView) ->
#   editor = editorView.getEditor()
#   if path.extname(editor.getPath()) is '.md'
#     editor.setSoftWrap(true)

atom.commands.add 'atom-text-editor.vim-mode-plus.insert-mode', 'custom:space', ->
  view = atom.views.getView atom.workspace.getActiveTextEditor()
  editor = @getModel()
  atom.commands.dispatch view, 'vim-mode-plus:activate-normal-mode'
  atom.commands.dispatch view, 'vim-mode-plus:insert-after'
  editor.insertText(' ')

atom.commands.add 'atom-text-editor.vim-mode-plus.insert-mode', 'custom:enter', ->
  view = atom.views.getView atom.workspace.getActiveTextEditor()
  editor = @getModel()
  atom.commands.dispatch view, 'vim-mode-plus:activate-normal-mode'
  atom.commands.dispatch view, 'vim-mode-plus:insert-after'
  editor.insertText('\n')
