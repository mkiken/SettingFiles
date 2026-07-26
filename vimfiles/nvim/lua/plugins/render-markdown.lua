return {
  "MeanderingProgrammer/render-markdown.nvim",
  ft = { "markdown" },
  dependencies = {
    "nvim-treesitter/nvim-treesitter",
    "nvim-tree/nvim-web-devicons",
  },
  opts = {
    enabled = true,
    render_modes = { "n", "c" },
    file_types = { "markdown" },
    sign = {
      enabled = false,
    },
    heading = {
      icons = { "# ", "## ", "### ", "#### ", "##### ", "###### " },
    },
    completions = {
      lsp = {
        enabled = true,
      },
    },
  },
  keys = {
    { "<Leader>mp", "<cmd>RenderMarkdown toggle<CR>", desc = "Markdown previewをトグルする" },
    { "<Leader>mP", "<cmd>RenderMarkdown preview<CR>", desc = "Markdown previewを横に開く" },
  },
}
