return {
  'petertriho/nvim-scrollbar',
  -- v2移行(issue #121)は11-02のオプション確定後に行う。それまで起動時警告を止める
  init = function()
    vim.g.scrollbar_v2_notice = false
  end,
  opts = {
    handle = {
      color = "#9399b2",
      blend = 60,
    },
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
