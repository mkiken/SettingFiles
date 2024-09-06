if vim.g.vscode then
  -- VSCode extension
  return {
    -- disable trouble
    { "hrsh7th/cmp-buffer", enabled = false },
    { "hrsh7th/cmp-nvim-lsp", enabled = false },
    { "hrsh7th/cmp-path", enabled = false },
    { "hrsh7th/nvim-cmp", enabled = false },
    { "neovim/nvim-lspconfig", enabled = false },
  }
else
  -- ordinary Neovim
  return {}
end
