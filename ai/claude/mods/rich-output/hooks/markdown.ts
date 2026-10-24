export type Block =
  | { kind: 'markdown'; text: string }
  | { kind: 'line'; text: string }

export type Span =
  | { kind: 'text'; text: string }
  | { kind: 'bold'; text: string }
  | { kind: 'code'; text: string }
  | { kind: 'link'; text: string }
  | { kind: 'path'; text: string }

const FENCE = /^\s*(```|~~~)/
// Tables and quotes keep the engine's own layout.
const KEEP_AS_MARKDOWN = /^\s*(\||>)/

// Fenced code, tables and quotes stay with the engine's Markdown so its
// highlighting is kept; every other line is drawn here. An unclosed fence
// (a reply still streaming) runs to the end of the text.
export function splitBlocks(text: string): Block[] {
  const blocks: Block[] = []
  let isFenced = false

  const pushMarkdown = (line: string) => {
    const last = blocks[blocks.length - 1]
    if (last?.kind === 'markdown') last.text += '\n' + line
    else blocks.push({ kind: 'markdown', text: line })
  }

  for (const line of text.split('\n')) {
    if (isFenced) {
      pushMarkdown(line)
      if (FENCE.test(line)) isFenced = false
    } else if (FENCE.test(line)) {
      isFenced = true
      pushMarkdown(line)
    } else if (KEEP_AS_MARKDOWN.test(line)) {
      pushMarkdown(line)
    } else {
      blocks.push({ kind: 'line', text: line })
    }
  }

  return blocks
}

// Alternatives are tried left to right at each position, so a code span or a
// link wins over the bold or path pattern that sits inside it.
const INLINE =
  /`([^`\n]+)`|\*\*([^*\n]+)\*\*|\[[^\]\n]+\]\([^)\s]+\)|https?:\/\/[^\s)]+|(?:\.{0,2}\/)?(?:[\w.-]+\/)+[\w.-]+\.\w+(?::\d+)?|\b[\w-]+(?:\.[\w-]+)*\.(?:ts|tsx|js|json|py|sh|zsh|md|toml|ya?ml|lua|rs|go)(?::\d+)?\b/g

// A backticked span that is only a file path is drawn as a path, not as code.
const PATH_ONLY =
  /^(?:(?:\.{0,2}\/)?(?:[\w.-]+\/)+[\w.-]+\.\w+|[\w-]+(?:\.[\w-]+)*\.(?:ts|tsx|js|json|py|sh|zsh|md|toml|ya?ml|lua|rs|go))(?::\d+)?$/

export function inlineSpans(line: string): Span[] {
  const spans: Span[] = []
  let at = 0

  for (const m of line.matchAll(INLINE)) {
    const start = m.index ?? 0
    if (start > at) spans.push({ kind: 'text', text: line.slice(at, start) })

    if (m[1] !== undefined) {
      spans.push({ kind: PATH_ONLY.test(m[1]) ? 'path' : 'code', text: m[1] })
    } else if (m[2] !== undefined) spans.push({ kind: 'bold', text: m[2] })
    else if (m[0].startsWith('[')) {
      spans.push({ kind: 'link', text: m[0].slice(1, m[0].indexOf(']')) })
    } else if (m[0].startsWith('http')) spans.push({ kind: 'link', text: m[0] })
    else spans.push({ kind: 'path', text: m[0] })

    at = start + m[0].length
  }

  if (at < line.length) spans.push({ kind: 'text', text: line.slice(at) })

  return spans
}

export type LineKind =
  | { kind: 'heading'; text: string }
  | { kind: 'list'; indent: string; marker: string; text: string }
  | { kind: 'plain'; text: string }

export function classifyLine(line: string): LineKind {
  const heading = /^#{1,6}\s+(.*)$/.exec(line)
  if (heading) return { kind: 'heading', text: heading[1] }

  const item = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/.exec(line)
  if (item) {
    const marker = /\d/.test(item[2]) ? item[2] : '•'
    return { kind: 'list', indent: item[1], marker, text: item[3] }
  }

  return { kind: 'plain', text: line }
}
