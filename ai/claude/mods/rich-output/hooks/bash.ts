export type CommandSpan = {
  kind: 'program' | 'option' | 'string' | 'path' | 'var' | 'operator' | 'text'
  text: string
}

// Longest alternative first, so `&&` is not read as two `&` and `2>&1` stays whole.
const OPERATOR = /^(?:&&|\|\||\d*>>?(?:&\d)?|[|;&<])/
const SEPARATES_COMMANDS = /^(?:&&|\|\||[|;&])$/
const ASSIGNMENT = /^[A-Za-z_]\w*=/

// Where the word that starts at `from` ends: quoted parts belong to the word,
// and an unclosed quote runs to the end of the command.
function wordEnd(command: string, from: number): number {
  let i = from

  while (i < command.length && !/[\s|;&<>]/.test(command[i])) {
    const c = command[i]
    if (c === '\\') {
      i += 2
    } else if (c === "'" || c === '"') {
      i++
      while (i < command.length && command[i] !== c) {
        i += c === '"' && command[i] === '\\' ? 2 : 1
      }
      i++
    } else {
      i++
    }
  }

  return Math.min(i, command.length)
}

export function commandSpans(command: string): CommandSpan[] {
  const spans: CommandSpan[] = []
  let at = 0
  let isCommandPosition = true

  while (at < command.length) {
    const rest = command.slice(at)
    const space = /^\s+/.exec(rest)
    if (space) {
      spans.push({ kind: 'text', text: space[0] })
      at += space[0].length
      continue
    }

    const op = OPERATOR.exec(rest)
    if (op) {
      spans.push({ kind: 'operator', text: op[0] })
      if (SEPARATES_COMMANDS.test(op[0])) isCommandPosition = true
      at += op[0].length
      continue
    }

    const end = wordEnd(command, at)
    const word = command.slice(at, end)
    at = end

    if (/^['"]/.test(word)) {
      spans.push({ kind: 'string', text: word })
    } else if (isCommandPosition && ASSIGNMENT.test(word)) {
      spans.push({ kind: 'var', text: word })
    } else if (isCommandPosition) {
      spans.push({ kind: 'program', text: word })
      isCommandPosition = false
    } else if (word.startsWith('-')) {
      spans.push({ kind: 'option', text: word })
    } else if (word.startsWith('$')) {
      spans.push({ kind: 'var', text: word })
    } else if (word.includes('/') || word.startsWith('~')) {
      spans.push({ kind: 'path', text: word })
    } else {
      spans.push({ kind: 'text', text: word })
    }
  }

  return spans
}
