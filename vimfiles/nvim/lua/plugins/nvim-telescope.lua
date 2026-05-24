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

local function executable(name)
  return vim.fn.executable(name) == 1
end

local function at_mention_path(path)
  if not path or path == "" then
    return nil
  end

  return "@" .. path
end

local function find_file_command(opts)
  opts = opts or {}

  if executable("rg") then
    local command = { "rg", "--files", "--color", "never" }
    if opts.max_depth then
      vim.list_extend(command, { "--max-depth", tostring(opts.max_depth) })
    end
    return command
  elseif executable("fd") then
    local command = { "fd", "--type", "f", "--color", "never" }
    if opts.max_depth then
      vim.list_extend(command, { "--max-depth", tostring(opts.max_depth) })
    end
    return command
  elseif executable("fdfind") then
    local command = { "fdfind", "--type", "f", "--color", "never" }
    if opts.max_depth then
      vim.list_extend(command, { "--max-depth", tostring(opts.max_depth) })
    end
    return command
  elseif executable("find") and vim.fn.has("win32") == 0 then
    return { "find", ".", "-type", "f" }
  elseif executable("where") then
    return { "where", "/r", ".", "*" }
  end

  return nil
end

local function preview_entry_path(entry, cwd)
  if not entry then
    return nil
  end

  local path = entry.path or entry.filename or entry.value or entry[1]
  if type(path) ~= "string" or path == "" then
    return nil
  end

  if vim.startswith(path, "/") or path:match("^%a:[/\\]") then
    return path
  end

  if vim.fs.joinpath then
    return vim.fs.joinpath(cwd, path)
  end

  return cwd .. "/" .. path
end

local function file_picker_previewer(cwd, mode_state)
  local previewers = require('telescope.previewers')
  local action_state = require('telescope.actions.state')

  return previewers.new_termopen_previewer({
    title = "File Preview",
    get_command = function(entry)
      local path = preview_entry_path(entry, mode_state.cwd or cwd)
      if not path then
        return nil
      end

      if mode_state.mode == "grep" then
        local query = action_state.get_current_line()
        if query == "" or not executable("rg") then
          return nil
        end

        return {
          "rg",
          "--context",
          "3",
          "--color=always",
          "--line-number",
          "--no-heading",
          "--smart-case",
          "--max-columns",
          "200",
          "--max-columns-preview",
          "--",
          query,
          path,
        }
      end

      if executable("bat") then
        return { "bat", "--style=numbers", "--color=always", "--line-range", ":200", path }
      elseif executable("batcat") then
        return { "batcat", "--style=numbers", "--color=always", "--line-range", ":200", path }
      end

      return { "sed", "-n", "1,200p", path }
    end,
  })
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
  local conf = require('telescope.config').values
  local finders = require('telescope.finders')
  local make_entry = require('telescope.make_entry')
  local pickers = require('telescope.pickers')
  local sorters = require('telescope.sorters')

  local mode_state = { mode = "files", cwd = cwd }

  local function new_file_finder(search_cwd, opts)
    local command = find_file_command(opts)
    if not command then
      return nil
    end

    return finders.new_oneshot_job(command, {
      cwd = search_cwd,
      entry_maker = make_entry.gen_from_file({ cwd = search_cwd }),
    })
  end

  local function new_grep_finder(search_cwd)
    return finders.new_job(function(prompt)
      if not prompt or prompt == "" then
        return nil
      end

      return {
        "rg",
        "--files-with-matches",
        "--hidden",
        "--glob",
        "!.git",
        "--color",
        "never",
        "--",
        prompt,
      }
    end, make_entry.gen_from_file({ cwd = search_cwd }), nil, search_cwd)
  end

  local function picker_sorter(mode, search_cwd)
    if mode == "grep" then
      return sorters.highlighter_only({})
    end

    return conf.file_sorter({ cwd = search_cwd })
  end

  local function insert_selected_paths(prompt_bufnr)
    local paths = {}
    local selected_cwd = mode_state.cwd or cwd
    local picker = action_state.get_current_picker(prompt_bufnr)
    local selections = picker:get_multi_selection()

    if #selections == 0 then
      selections = { action_state.get_selected_entry() }
    end

    for _, entry in ipairs(selections) do
      local path
      if mode_state.mode == "desktop" then
        path = preview_entry_path(entry, selected_cwd)
      else
        path = telescope_entry_path(entry, selected_cwd)
      end

      if path then
        table.insert(paths, at_mention_path(path))
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
  end

  local function switch_mode(prompt_bufnr)
    local next_mode = mode_state.mode == "files" and "grep" or "files"
    if next_mode == "grep" and not executable("rg") then
      vim.notify("rg not found for @ file picker grep mode", vim.log.levels.WARN)
      return
    end

    local finder = next_mode == "grep" and new_grep_finder(cwd) or new_file_finder(cwd)
    if not finder then
      vim.notify("No file search command found for @ file picker", vim.log.levels.WARN)
      return
    end

    mode_state.mode = next_mode
    mode_state.cwd = cwd

    local picker = action_state.get_current_picker(prompt_bufnr)
    picker.sorter = picker_sorter(next_mode, cwd)
    picker.sorter:_init()
    picker:refresh(finder, {
      reset_prompt = true,
      new_prefix = next_mode == "grep" and "Grep> " or "Files> ",
    })
  end

  local function switch_desktop_mode(prompt_bufnr)
    local next_mode = mode_state.mode == "desktop" and "files" or "desktop"
    local next_cwd = next_mode == "desktop" and normalize_dir("~/Desktop") or cwd
    if not next_cwd then
      vim.notify("Desktop directory not found for @ file picker", vim.log.levels.WARN)
      return
    end

    local finder = new_file_finder(next_cwd, next_mode == "desktop" and { max_depth = 1 } or nil)
    if not finder then
      vim.notify("No file search command found for @ file picker", vim.log.levels.WARN)
      return
    end

    mode_state.mode = next_mode
    mode_state.cwd = next_cwd

    local picker = action_state.get_current_picker(prompt_bufnr)
    picker.sorter = picker_sorter(next_mode, next_cwd)
    picker.sorter:_init()
    picker:refresh(finder, {
      reset_prompt = true,
      new_prefix = next_mode == "desktop" and "Desktop> " or "Files> ",
    })
  end

  local initial_finder = new_file_finder(cwd)
  if not initial_finder then
    vim.notify("No file search command found for @ file picker", vim.log.levels.WARN)
    return
  end

  pickers.new({
    cwd = cwd,
    prompt_title = "Insert @ File",
    prompt_prefix = "Files> ",
  }, {
    finder = initial_finder,
    previewer = file_picker_previewer(cwd, mode_state),
    sorter = picker_sorter("files", cwd),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        insert_selected_paths(prompt_bufnr)
      end)

      map({ "i", "n" }, "<C-s>", switch_mode)
      map({ "i", "n" }, "<C-d>", switch_desktop_mode)

      return true
    end,
  }):find()
end

return {
  'nvim-telescope/telescope.nvim',
  dependencies = {
    'nvim-lua/plenary.nvim',
    'nvim-telescope/telescope-file-browser.nvim',
    {
      'nvim-telescope/telescope-frecency.nvim',
      version = '*',
    },
  },
  keys = {
    { "<leader>b", function() require('telescope.builtin').buffers() end, desc="Telescope buffers" },
    { "<leader>fcm", function() require('telescope.builtin').commands() end, desc="Lists available plugin/user commands and runs them on <cr>" },
    { "<leader>fcs", function() require('telescope.builtin').color_scheme() end, desc="Lists available colorschemes and applies them on <cr>" },
    { "<leader>ff", function() require('telescope').extensions.frecency.frecency({ workspace = "CWD" }) end, desc="Telescope frecency files" },
    { "<leader>F", function() require('telescope.builtin').find_files() end, desc="Telescope find files" },
    { "<leader>@", insert_at_file_paths, desc="Insert @ file paths" },
    { "<leader>gd", function() require('telescope.builtin').live_grep() end, desc="Search for a string in your current working directory and get results live as you type, respects .gitignore" },
    { "<leader>gf", function() require('telescope.builtin').current_buffer_fuzzy_find() end, desc="Live fuzzy search inside of the currently open buffer" },
    { "<leader>hc", function() require('telescope.builtin').command_history() end, desc="Lists commands that were executed recently, and reruns them on <cr>" },
    { "<leader>hs", function() require('telescope.builtin').search_history() end, desc="Lists searches that were executed recently, and reruns them on <cr>" },
    { "<leader>ft", function() require('telescope').extensions.file_browser.file_browser({ path = "%:p:h", select_buffer = true }) end, desc="Telescope file browser" },
  },
  config = function()
    local telescope = require('telescope')
    telescope.load_extension('fzf')
    telescope.load_extension('file_browser')
    telescope.load_extension('frecency')
  end
}
