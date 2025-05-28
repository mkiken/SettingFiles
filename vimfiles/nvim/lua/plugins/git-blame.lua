return {
  'f-person/git-blame.nvim',
  opts = {
    enabled = true,  -- if you want to enable the plugin
    message_template = " <author>, <date> - <summary>", -- template for the blame message
    date_format = "%r", -- template for the date
    virtual_text_column = 1,  -- virtual text start column
},
  -- 起動後に遅延読み込み
  event = "VeryLazy",
}
