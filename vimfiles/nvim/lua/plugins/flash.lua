return {
  "folke/flash.nvim",
  event = "VeryLazy",
  ---@type Flash.Config
  opts = {},
  config = function(_, opts)
    require("flash").setup(opts)

    -- 1文字目と2文字目で明確に異なる色を設定
    vim.api.nvim_set_hl(0, "FlashLabel1", { fg = "#00dfff", bg = "#2d2d2d", bold = true })  -- 青/シアン系
    vim.api.nvim_set_hl(0, "FlashLabel2", { fg = "#ff007c", bg = "#2d2d2d", bold = true })  -- ピンク系
  end,
  -- stylua: ignore
  keys = {
    {
      "s",
      mode = { "n", "x", "o" },
      function()
        local Flash = require("flash")

        -- 1回目のジャンプ用：label1 + label2 の2文字表示
        local function format_double(opts)
          return {
            { opts.match.label1, "FlashLabel1" },
            { opts.match.label2, "FlashLabel2" },
          }
        end

        -- 2回目のジャンプ用：label2 のみ表示
        local function format_single(opts)
          return {
            { opts.match.label2, "FlashLabel2" },
          }
        end

        Flash.jump({
          search = { mode = "search" },
          label = { after = { 0, 1 }, before = false, uppercase = false, format = format_double },
          action = function(match, state)
            state:hide()
            Flash.jump({
              search = { max_length = 0 },
              highlight = { matches = false },
              label = { after = { 0, 1 }, before = false, format = format_single },
              matcher = function(win)
                return vim.tbl_filter(function(m)
                  return m.label == match.label and m.win == win
                end, state.results)
              end,
              labeler = function(matches)
                for _, m in ipairs(matches) do
                  m.label = m.label2
                end
              end,
            })
          end,
          labeler = function(matches, state)
            local labels = state:labels()
            for m, match in ipairs(matches) do
              match.label1 = labels[math.floor((m - 1) / #labels) + 1]
              match.label2 = labels[(m - 1) % #labels + 1]
              match.label = match.label1
            end
          end,
        })
      end,
      desc = "Flash 2-char",
    },
    { "S", mode = { "n", "x", "o" }, function() require("flash").treesitter() end, desc = "Flash Treesitter" },
  },
}
