if vim.g.vscode then
  -- VSCode extension
  return {
    -- disable trouble
    { "neovim/nvim-lspconfig", enabled = false },
  }
else
  -- ordinary Neovim
end
