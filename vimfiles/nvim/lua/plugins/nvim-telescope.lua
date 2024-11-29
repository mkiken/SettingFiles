local telescope = require('telescope')
local builtin = require('telescope.builtin')
return {
  'nvim-telescope/telescope.nvim',
  dependencies = { 'nvim-lua/plenary.nvim' },
  keys = {
    { "<leader>ff", function() builtin.find_files() end, desc="Telescope find files" },
    { "<leader>fg", function() builtin.live_grep() end, desc="Telescope live grep" },
    { "<leader>fb", function() builtin.buffers() end, desc="Telescope buffers" },
    { "<leader>fn", function() builtin.help_tags() end, desc="Telescope help tags" }
  },
  config = function()
    telescope.load_extension('fzf')
  end
}
