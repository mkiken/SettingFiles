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
  editor = @getModel()
  insertWithModeChange(editor, ' ')

atom.commands.add 'atom-text-editor.vim-mode-plus.insert-mode', 'custom:enter', ->
  editor = @getModel()
  insertWithModeChange(editor, '\n')

insertWithModeChange = (editor, text) ->
  view = atom.views.getView atom.workspace.getActiveTextEditor()
  column = editor.getCursorBufferPosition().column
  atom.commands.dispatch view, 'vim-mode-plus:activate-normal-mode'
  if column is 0
    atom.commands.dispatch view, 'vim-mode-plus:activate-insert-mode'
  else
    atom.commands.dispatch view, 'vim-mode-plus:insert-after'

  editor.insertText(text)
