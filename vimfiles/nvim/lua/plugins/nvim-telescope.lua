return {
  'nvim-telescope/telescope.nvim',
  dependencies = { 'nvim-lua/plenary.nvim' },
  keys = {
    { "<leader>fb", function() require('telescope.builtin').buffers() end, desc="Telescope buffers" },
    { "<leader>fc", function() require('telescope.builtin').commands() end, desc="Lists available plugin/user commands and runs them on <cr>" },
    { "<leader>ff", function() require('telescope.builtin').find_files() end, desc="Telescope find files" },
    { "<leader>fgd", function() require('telescope.builtin').live_grep() end, desc="Search for a string in your current working directory and get results live as you type, respects .gitignore" },
    { "<leader>fgf", function() require('telescope.builtin').current_buffer_fuzzy_find() end, desc="Live fuzzy search inside of the currently open buffer" },
    { "<leader>fhc", function() require('telescope.builtin').command_history() end, desc="Lists commands that were executed recently, and reruns them on <cr>" },
    { "<leader>fhs", function() require('telescope.builtin').search_history() end, desc="Lists searches that were executed recently, and reruns them on <cr>" },
    { "<leader>ft", function() require('telescope.builtin').color_scheme() end, desc="Lists available colorschemes and applies them on <cr>" },
  },
  config = function()
    require('telescope').load_extension('fzf')
  end
}
