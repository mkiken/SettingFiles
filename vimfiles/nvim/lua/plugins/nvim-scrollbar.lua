return {
  'petertriho/nvim-scrollbar',
  opts = {
    handlers = {
      -- trueにすると文字列の一番右の文字が見えなくなることがある
      cursor = false,
    },
  },
  dependencies = {
    "kevinhwang91/nvim-hlslens",
    "lewis6991/gitsigns.nvim",
  },
}
