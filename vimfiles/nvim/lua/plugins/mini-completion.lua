return {
  'echasnovski/mini.completion',
  version = false,
  config = -- No need to copy this inside `setup()`. Will be used automatically.
{
  -- Module mappings. Use `''` (empty string) to disable one. Some of them
  -- might conflict with system mappings.
  mappings = {
    -- Scroll info/signature window down/up. When overriding, check for
    -- conflicts with built-in keys for popup menu (like `<C-u>`/`<C-o>`
    -- for 'completefunc'/'omnifunc' source function; or `<C-n>`/`<C-p>`).
    scroll_down = '',
    scroll_up = '',
  },
}
}
