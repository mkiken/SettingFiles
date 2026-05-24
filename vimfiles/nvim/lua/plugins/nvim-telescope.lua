local function normalize_dir(path)
  if not path or path == "" then
    return nil
  end

  local expanded = vim.fn.expand(path)
  if vim.fn.isdirectory(expanded) ~= 1 then
    return nil
  end

  local absolute = vim.fn.fnamemodify(expanded, ":p")
  return vim.uv.fs_realpath(absolute) or absolute
end

local function git_root(path)
  local dir = normalize_dir(path)
  if not dir then
    return nil
  end

  local output = vim.fn.systemlist({ "git", "-C", dir, "rev-parse", "--show-toplevel" })
  if vim.v.shell_error ~= 0 or not output[1] or output[1] == "" then
    return nil
  end

  return normalize_dir(output[1])
end

local function prompt_file_picker_cwd()
  local cwd = normalize_dir(vim.fn.getcwd())
  local root = git_root(cwd)
  if root then
    return root
  end

  local claude_project_dir = normalize_dir(vim.env.CLAUDE_PROJECT_DIR)
  if claude_project_dir then
    return git_root(claude_project_dir) or claude_project_dir
  end

  return cwd
end

local function relative_path(path, cwd)
  if not path or path == "" then
    return nil
  end

  if vim.fs.relpath and vim.startswith(path, "/") then
    path = vim.fs.relpath(cwd, path) or path
  end

  return path:gsub("^%./", "")
end

local function telescope_entry_path(entry, cwd)
  if not entry then
    return nil
  end

  return relative_path(entry.value or entry.filename or entry.path or entry[1], cwd)
end

local function insert_at_file_paths()
  local cwd = prompt_file_picker_cwd()
  if not cwd then
    vim.notify("No directory found for @ file picker", vim.log.levels.WARN)
    return
  end

  local insert_win = vim.api.nvim_get_current_win()
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')

  require('telescope.builtin').find_files({
    cwd = cwd,
    prompt_title = "Insert @ File",
    attach_mappings = function(prompt_bufnr)
      actions.select_default:replace(function()
        local paths = {}
        local picker = action_state.get_current_picker(prompt_bufnr)
        local selections = picker:get_multi_selection()

        if #selections == 0 then
          selections = { action_state.get_selected_entry() }
        end

        for _, entry in ipairs(selections) do
          local path = telescope_entry_path(entry, cwd)
          if path then
            table.insert(paths, "@" .. path)
          end
        end

        actions.close(prompt_bufnr)

        if #paths == 0 then
          return
        end

        vim.schedule(function()
          if vim.api.nvim_win_is_valid(insert_win) then
            vim.api.nvim_set_current_win(insert_win)
          end
          vim.api.nvim_put({ table.concat(paths, " ") .. " " }, "c", true, true)
        end)
      end)

      return true
    end,
  })
end

return {
  'nvim-telescope/telescope.nvim',
  dependencies = {
    'nvim-lua/plenary.nvim',
    'nvim-telescope/telescope-file-browser.nvim',
  },
  keys = {
    { "<leader>fb", function() require('telescope.builtin').buffers() end, desc="Telescope buffers" },
    { "<leader>fcm", function() require('telescope.builtin').commands() end, desc="Lists available plugin/user commands and runs them on <cr>" },
    { "<leader>fcs", function() require('telescope.builtin').color_scheme() end, desc="Lists available colorschemes and applies them on <cr>" },
    { "<leader>ff", function() require('telescope.builtin').find_files() end, desc="Telescope find files" },
    { "<leader>f@", insert_at_file_paths, desc="Insert @ file paths" },
    { "<leader>fgd", function() require('telescope.builtin').live_grep() end, desc="Search for a string in your current working directory and get results live as you type, respects .gitignore" },
    { "<leader>fgf", function() require('telescope.builtin').current_buffer_fuzzy_find() end, desc="Live fuzzy search inside of the currently open buffer" },
    { "<leader>fhc", function() require('telescope.builtin').command_history() end, desc="Lists commands that were executed recently, and reruns them on <cr>" },
    { "<leader>fhs", function() require('telescope.builtin').search_history() end, desc="Lists searches that were executed recently, and reruns them on <cr>" },
    { "<leader>ft", function() require('telescope').extensions.file_browser.file_browser({ path = "%:p:h", select_buffer = true }) end, desc="Telescope file browser" },
  },
  config = function()
    require('telescope').load_extension('fzf')
    require('telescope').load_extension('file_browser')
  end
}
