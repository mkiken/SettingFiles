-- Herdr の同タブで動く AI CLI ペインへ、現在のファイルパスと行範囲を送る。
-- AI CLI を nvim の :terminal 内で描画すると表示が崩れるため、CLI は Herdr 側のペインで動かす。
local M = {}

local AI_AGENTS = { claude = true, codex = true, gemini = true }

-- 同タブに AI ペインが無いときの起動候補。新ペインの対話 zsh でそのまま実行されるため、
-- エイリアスに引数を足してモデルや effort を固定した行も書ける。
M.launch_commands = {
  "clo", "cls", "clf", "clh", "cloeh", "clseh", "cleh", "clmx",
  "cxs", "cxa", "cxt", "cxl", "cxeh", "cxteh", "cxmx",
  "gmf", "gmp", "gmmx",
}

local function herdr_bin()
  return vim.env.HERDR_BIN_PATH or "herdr"
end

local function err(msg)
  vim.notify("herdr_ai: " .. msg, vim.log.levels.ERROR)
end

-- 自ペインと同じタブにいる AI ペインの一覧を返す。失敗時は nil とエラー文言。
local function find_ai_panes()
  local self_id = vim.env.HERDR_PANE_ID
  if not self_id or self_id == "" then
    return nil, "Herdr 内の nvim ではありません (HERDR_PANE_ID 未設定)"
  end
  local out = vim.system({ herdr_bin(), "pane", "list" }, { text = true }):wait()
  if out.code ~= 0 then
    return nil, "herdr pane list に失敗しました"
  end
  local ok, decoded = pcall(vim.json.decode, out.stdout)
  local panes = ok and decoded.result and decoded.result.panes
  if not panes then
    return nil, "herdr pane list の出力を解釈できません"
  end
  local tab_id
  for _, pane in ipairs(panes) do
    if pane.pane_id == self_id then
      tab_id = pane.tab_id
    end
  end
  local found = {}
  for _, pane in ipairs(panes) do
    if pane.tab_id == tab_id and pane.pane_id ~= self_id and AI_AGENTS[pane.agent] then
      table.insert(found, pane)
    end
  end
  return found
end

-- 送信先ペインの cwd 配下なら相対パス、それ以外は絶対パスにする。
local function display_path(abs_path, pane_cwd)
  local prefix = (pane_cwd or ""):gsub("/+$", "") .. "/"
  if pane_cwd and pane_cwd ~= "" and abs_path:sub(1, #prefix) == prefix then
    return abs_path:sub(#prefix + 1)
  end
  return abs_path
end

local function send(pane, line_spec, abs_path)
  local text = display_path(abs_path, pane.cwd) .. (line_spec or "") .. " "
  -- send-text は <pane_id> <text> の2引数固定で `--` を解釈しない。Enter は送らない。
  local out = vim.system({ herdr_bin(), "pane", "send-text", pane.pane_id, text }, { text = true }):wait()
  if out.code ~= 0 then
    err("herdr pane send-text に失敗しました")
  end
end

local function launch_script()
  local base = vim.env.SET or (vim.env.HOME .. "/Desktop/repository/SettingFiles")
  return vim.fs.joinpath(base, "shell/herdr/herdr-ai-launch.sh")
end

-- 右ペインで cmd を起動して入力待ちになるまで待ち、そのペインへ参照を送る。
-- 最大 ~85s かかるため非同期で実行し、nvim の操作を止めない。
local function launch_and_send(cmd, cwd, line_spec, abs_path)
  vim.notify("herdr_ai: 起動中: " .. cmd)
  vim.system({ launch_script(), vim.env.HERDR_PANE_ID, cwd, cmd }, { text = true }, function(out)
    vim.schedule(function()
      if out.code ~= 0 then
        local msg = vim.trim(out.stderr or "")
        err(msg ~= "" and msg or ("AI ペインの起動に失敗しました: " .. cmd))
        return
      end
      send({ pane_id = vim.trim(out.stdout), cwd = cwd }, line_spec, abs_path)
    end)
  end)
end

local function with_target_pane(line_spec_fn)
  local panes, e = find_ai_panes()
  if not panes then
    err(e)
    return
  end
  -- 選択範囲とバッファは選択ダイアログ表示前に確定させる (ダイアログがモードや現在バッファを変えるため)。
  local abs_path = vim.api.nvim_buf_get_name(0)
  if abs_path == "" then
    err("ファイルに保存されていないバッファです")
    return
  end
  local line_spec = line_spec_fn()
  if #panes == 0 then
    local cwd = vim.fn.getcwd()
    vim.ui.select(M.launch_commands, { prompt = "AI ペインが無いため起動する CLI" }, function(cmd)
      if cmd then
        launch_and_send(cmd, cwd, line_spec, abs_path)
      end
    end)
    return
  end
  if #panes == 1 then
    send(panes[1], line_spec, abs_path)
    return
  end
  vim.ui.select(panes, {
    prompt = "送信先 AI ペイン",
    format_item = function(p)
      return string.format("%s (%s)", p.agent, p.pane_id)
    end,
  }, function(choice)
    if choice then
      send(choice, line_spec, abs_path)
    end
  end)
end

-- ノーマルモードは現在行、ビジュアルモードは選択行範囲を `path:12` / `path:12-20` で送る。
function M.send_location()
  with_target_pane(function()
    local mode = vim.fn.mode()
    local first, last
    if mode == "v" or mode == "V" or mode == "\22" then
      first, last = vim.fn.line("v"), vim.fn.line(".")
      if first > last then
        first, last = last, first
      end
    else
      first = vim.fn.line(".")
      last = first
    end
    return first == last and (":" .. first) or (":" .. first .. "-" .. last)
  end)
end

function M.send_file()
  with_target_pane(function()
    return ""
  end)
end

vim.keymap.set({ "n", "x" }, "<leader>at", M.send_location, { desc = "Herdr AI: send file:line" })
vim.keymap.set("n", "<leader>af", M.send_file, { desc = "Herdr AI: send file" })

return M
