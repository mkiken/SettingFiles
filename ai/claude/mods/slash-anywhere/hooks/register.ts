import type { Register } from 'claude-code'

const MAX_ROWS = 20

export const register: Register = on => {
  on('prompt.autocomplete', { token: /^\// }, async ($, e, next) => {
    const base = await next(e)
    const isLeading = e.start === 0
    // Text anywhere after the cursor, on this line or a later one.
    const hasTextAfter = /\S/.test(e.text.slice(e.cursor))

    // The engine already completes a leading `/word` with nothing after it.
    if (!isLeading || !hasTextAfter) return base

    // Only a word glued to the cursor needs a space; whitespace already there stays.
    const sep = /\S/.test(e.text[e.cursor] ?? '') ? ' ' : ''
    const typed = e.token.slice(1).toLowerCase()
    const seen = new Set<string>()
    const rows = (await $.command.list())
      .filter(c => {
        // A plugin skill matches on its bare name too: `/deploy` finds `p:deploy`.
        const bare = c.name.slice(c.name.lastIndexOf(':') + 1)
        const isMatch =
          c.name.toLowerCase().startsWith(typed) ||
          bare.toLowerCase().startsWith(typed)

        if (!isMatch || seen.has(c.name)) return false
        seen.add(c.name)
        return true
      })
      .slice(0, MAX_ROWS)
      .map(c => ({
        text: `/${c.name}${sep}`,
        label: `/${c.name}`,
        description: c.description,
      }))

    return { suggestions: [...base.suggestions, ...rows] }
  })
}
