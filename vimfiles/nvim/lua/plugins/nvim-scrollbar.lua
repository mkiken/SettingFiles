return {
  'petertriho/nvim-scrollbar',
  opts = {
    providers = {
      -- trueにすると文字列の一番右の文字が見えなくなることがある
      cursor = false,
      gitsigns = true,
    },
    scrollbar = {
      thumb = {
        highlight = { bg = "#9399b2" },
        blend = 60,
      },
    },
  },
  dependencies = {
    "lewis6991/gitsigns.nvim",
  },
}
