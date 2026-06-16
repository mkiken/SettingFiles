return {
  {
    "gregorias/coop.nvim",
    lazy = true,
  },
  {
    "gregorias/coerce.nvim",
    tag = "v5.0.0",
    dependencies = {
      "gregorias/coop.nvim",
    },
    config = function()
      require("coerce").setup()
    end,
    keys = {
      {
        "cr",
        function()
          require("coerce.keymaps").action({
            selector = require("coerce.selector").select_current_word,
            transformer = require("coerce.transformer").transform_local,
          })
        end,
        mode = "n",
        desc = "Coerce word",
        silent = true,
      },
      { "gcr", "<Plug>(coerce-motion)", mode = "n", desc = "Coerce motion", silent = true },
      { "gcr", "<Plug>(coerce-visual)", mode = "x", desc = "Coerce selection", silent = true },
    },
  },
}
