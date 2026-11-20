-- 基本オプションの設定
require('options')

-- キーマップの設定
require('keymaps')

-- キーマップ以外のneovim apiの設定
require('api')

-- AI CLIの外部エディタバッファでスキル/コマンドを補完
require('ai_prompt_complete')

-- Herdr の AI ペインへファイルパスと行番号を送信
require('herdr_ai')

-- プラグインの設定
require("config.lazy")

