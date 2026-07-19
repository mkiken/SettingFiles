-- PlantUML(.puml等)のシンタックスハイライト。
-- treesitterにPlantUMLパーサが無いため従来型vim syntaxプラグインを使う。
-- filetype検出はプラグイン同梱のftdetectがあるが、ft遅延ロードとの
-- ニワトリ卵問題を避けるため vim.filetype.add で起動時に確実に検出させる。
vim.filetype.add({
  extension = {
    puml = "plantuml",
    pu = "plantuml",
    iuml = "plantuml",
    plantuml = "plantuml",
    -- .uml は他形式と衝突しうるため含めない（必要なら後で追加）
  },
  pattern = {
    [".*%.wsd"] = "plantuml", -- 任意: PlantUML拡張子の一種。不要なら削除可
  },
})

return {
  "aklt/plantuml-syntax",
  ft = "plantuml",
}
