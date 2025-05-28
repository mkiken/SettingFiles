return {
  'akinsho/bufferline.nvim',
  config = function()
    local bufferline = require('bufferline')
    bufferline.setup {
      options = {
        style_preset = {
          bufferline.style_preset.no_italic,
          bufferline.style_preset.no_bold
        },
        hover = {
          enabled = true,
          delay = 200,
          reveal = { 'close' }
        },
        diagnostics = "nvim_lsp",
      }
    }
  end
}
