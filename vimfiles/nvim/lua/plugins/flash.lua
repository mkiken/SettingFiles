return {
  "folke/flash.nvim",
  event = "VeryLazy",
  ---@type Flash.Config
  opts = {
    jump = {
      autojump = true, -- マッチが1つの場合は自動ジャンプ
    },
    label = {
      uppercase = false,
    },
  },
  -- stylua: ignore
  keys = {
    {
      "s",
      mode = { "n", "x", "o" },
      function()
        local Flash = require("flash")

        -- 2文字ラベル用フォーマット
        local function format_double(opts)
          return {
            { opts.match.label1, "FlashMatch" },
            { opts.match.label2, "FlashLabel" },
          }
        end

        -- 2回目ジャンプ用（label2のみ）
        local function format_single(opts)
          return {
            { opts.match.label2, "FlashLabel" },
          }
        end

        Flash.jump({
          search = { mode = "search" },
          label = { after = { 0, 1 }, before = false, uppercase = false },
          labeler = function(matches, state)
            local labels = state:labels()
            local num_labels = #labels

            -- マッチ数がラベル数以下なら1文字ラベル（標準動作）
            if #matches <= num_labels then
              for i, match in ipairs(matches) do
                match.label = labels[i]
              end
            else
              -- マッチ数が多い場合は2文字ラベル
              for i, match in ipairs(matches) do
                match.label1 = labels[math.floor((i - 1) / num_labels) + 1]
                match.label2 = labels[(i - 1) % num_labels + 1]
                match.label = match.label1
              end
              -- 2文字モード用のフォーマットを設定
              state.opts.label.format = format_double
            end
          end,
          action = function(match, state)
            -- 1文字モード（label1がない）なら直接ジャンプ
            if not match.label1 then
              require("flash.jump").jump(match, state)
              require("flash.jump").on_jump(state)
              return
            end

            -- 2文字モード: 同じlabel1を持つマッチをlabel2で絞り込み
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
        })
      end,
      desc = "Flash",
    },
    { "S", mode = { "n", "x", "o" }, function() require("flash").treesitter() end, desc = "Flash Treesitter" },
  },
}
