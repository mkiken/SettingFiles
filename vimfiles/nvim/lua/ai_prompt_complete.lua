-- Claude Code / Codex / Gemini CLI の「外部エディタで編集」バッファで、
-- 1行目の先頭文字から始まるスキル/コマンド名を補完する。
--   claude: /name   codex: $name   gemini: /name (custom commands のみ)
local M = {}

local home = vim.uv.os_homedir()
local items_cache = {}

-- 一時ファイル名からツールを判定する
local function detect(path)
  local base = vim.fs.basename(path)
  if base:match('^claude%-prompt%-.*%.md$') then
    return 'claude'
  elseif path:match('/gemini%-edit%-[^/]+/buffer%.txt$') then
    return 'gemini'
  elseif path:find(home .. '/.codex/editor/', 1, true) or base:match('^%.tmp.*%.md$') then
    return 'codex'
  end
end

local TRIGGER = { claude = '/', codex = '$', gemini = '/' }

local function strip(value)
  return (value:gsub('^%s*["\']?', ''):gsub('["\']?%s*$', ''))
end

-- SKILL.md の frontmatter から name / description を読む（1行値のみ）
local function read_frontmatter(file)
  local name, desc
  local in_block = false
  for line in io.lines(file) do
    if line:match('^%-%-%-%s*$') then
      if in_block then break end
      in_block = true
    elseif in_block then
      name = name or line:match('^name:%s*(.+)$')
      desc = desc or line:match('^description:%s*(.+)$')
    end
  end
  return name and strip(name), desc and strip(desc)
end

local function add(items, seen, word, desc)
  if word ~= '' and not seen[word] then
    seen[word] = true
    items[#items + 1] = { word = word, menu = desc and desc:sub(1, 60) or '' }
  end
end

local function scan_skills(items, seen, dir, prefix)
  for _, file in ipairs(vim.fn.glob(dir .. '/*/SKILL.md', false, true)) do
    local name, desc = read_frontmatter(file)
    name = name or vim.fs.basename(vim.fs.dirname(file))
    add(items, seen, (prefix or '') .. name, desc)
  end
end

-- commands/ 配下のファイルを、サブディレクトリを ':' 区切りの名前空間にして列挙する
local function scan_commands(items, seen, dir, ext)
  for _, file in ipairs(vim.fn.glob(dir .. '/**/*.' .. ext, false, true)) do
    local rel = file:sub(#dir + 2):gsub('%.' .. ext .. '$', ''):gsub('/', ':')
    local desc
    for line in io.lines(file) do
      desc = line:match('^description%s*=%s*(.+)$') or line:match('^description:%s*(.+)$')
      if desc then break end
    end
    add(items, seen, rel, desc and strip(desc))
  end
end

-- cwd から git root までの各ディレクトリ（root が無ければ cwd のみ）
local function project_dirs()
  local cwd = vim.uv.cwd()
  local root = vim.fs.root(cwd, '.git') or cwd
  local dirs = { cwd }
  for dir in vim.fs.parents(cwd) do
    if #dir < #root then break end
    dirs[#dirs + 1] = dir
  end
  return dirs
end

local function collect(tool)
  local items, seen = {}, {}
  local dirs = project_dirs()
  if tool == 'claude' then
    for _, dir in ipairs(dirs) do
      scan_skills(items, seen, dir .. '/.claude/skills')
      scan_commands(items, seen, dir .. '/.claude/commands', 'md')
    end
    scan_skills(items, seen, home .. '/.claude/skills')
    scan_commands(items, seen, home .. '/.claude/commands', 'md')
    -- plugin cache は <marketplace>/<plugin>/<version>/skills。同名は最初の版を採用
    for _, plugin in ipairs(vim.fn.glob(home .. '/.claude/plugins/cache/*/*', false, true)) do
      local versions = vim.fn.glob(plugin .. '/*', false, true)
      table.sort(versions)
      local latest = versions[#versions]
      if latest then
        scan_skills(items, seen, latest .. '/skills', vim.fs.basename(plugin) .. ':')
      end
    end
  elseif tool == 'codex' then
    for _, dir in ipairs(dirs) do
      scan_skills(items, seen, dir .. '/.agents/skills')
    end
    scan_skills(items, seen, home .. '/.agents/skills')
    scan_skills(items, seen, home .. '/.codex/skills')
  elseif tool == 'gemini' then
    for _, dir in ipairs(dirs) do
      scan_commands(items, seen, dir .. '/.gemini/commands', 'toml')
    end
    scan_commands(items, seen, home .. '/.gemini/commands', 'toml')
  end
  table.sort(items, function(a, b) return a.word < b.word end)
  return items
end

-- 1行目・0列目がトリガー文字で、カーソルまでが空白を含まない時だけ補完する
function M.omnifunc(findstart, base)
  if findstart == 1 then
    local lnum, col = unpack(vim.api.nvim_win_get_cursor(0))
    local line = vim.api.nvim_get_current_line()
    local trigger = TRIGGER[vim.b.ai_prompt_tool]
    if lnum ~= 1 or line:sub(1, 1) ~= trigger or line:sub(1, col):find('%s') then
      return -3
    end
    return 1
  end
  local bufnr = vim.api.nvim_get_current_buf()
  items_cache[bufnr] = items_cache[bufnr] or collect(vim.b.ai_prompt_tool)
  local lower = base:lower()
  return vim.tbl_filter(function(item)
    return item.word:lower():sub(1, #lower) == lower
  end, items_cache[bufnr])
end

local function setup(buf)
  local tool = detect(vim.api.nvim_buf_get_name(buf))
  if not tool then return end
  vim.b[buf].ai_prompt_tool = tool
  vim.bo[buf].omnifunc = "v:lua.require'ai_prompt_complete'.omnifunc"
  -- mini.completion の自動補完を omnifunc 経由にする
  vim.b[buf].minicompletion_config = { fallback_action = '<C-x><C-o>' }
end

vim.api.nvim_create_autocmd({ 'BufReadPost', 'BufNewFile', 'FileType' }, {
  group = vim.api.nvim_create_augroup('ai_prompt_complete', { clear = true }),
  callback = function(args) setup(args.buf) end,
})

vim.api.nvim_create_autocmd('BufDelete', {
  callback = function(args) items_cache[args.buf] = nil end,
})

return M
