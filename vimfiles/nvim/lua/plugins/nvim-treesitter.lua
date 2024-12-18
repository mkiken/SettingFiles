return {
  "nvim-treesitter/nvim-treesitter", build = ":TSUpdate",
  config = true,
  dependencies = {
    {
      'nvim-treesitter/nvim-treesitter-textobjects',
      config = function()
        require'nvim-treesitter.configs'.setup {
          textobjects = {
            select = {
              enable = true,
              lookahead = true,
              keymaps = {
                ["af"] = "@function.outer",
                ["if"] = "@function.inner",
                ["ac"] = "@class.outer",
                ["ic"] = "@class.inner",
              },
            },
            move = {
              enable = true,
              set_jumps = true,
              goto_next_start = {
                ["]m"] = "@function.outer",
                ["]c"] = "@class.outer",
              },
              goto_previous_start = {
                ["[m"] = "@function.outer",
                ["[c"] = "@class.outer",
              },
            },
          },
        }
      end
    }
  }
}
