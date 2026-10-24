import type { Register } from 'claude-code'

import { classifyLine, inlineSpans, splitBlocks } from './markdown'
import type { Span } from './markdown'

// ANSI color names follow the terminal palette.
const COLOR = {
  heading: 'magenta',
  code: 'cyan',
  path: 'cyan',
  link: 'blue',
  marker: 'yellow',
  ok: 'green',
  error: 'red',
  command: 'cyan',
} as const

export const register: Register = on => {
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.isSummary) return next(e)

    const { Box, Text, Markdown } = $.ui.resolve(e)

    const spans = (items: Span[]) =>
      items.map(s => {
        switch (s.kind) {
          case 'bold':
            return <Text bold>{s.text}</Text>
          case 'code':
            return <Text color={COLOR.code}>{s.text}</Text>
          case 'path':
            return <Text color={COLOR.path}>{s.text}</Text>
          case 'link':
            return (
              <Text color={COLOR.link} underline>
                {s.text}
              </Text>
            )
          default:
            return s.text
        }
      })

    const rows = splitBlocks(e.props.text).map(block => {
      if (block.kind === 'markdown') return <Markdown text={block.text} />

      const line = classifyLine(block.text)
      if (line.kind === 'heading') {
        return (
          <Text bold color={COLOR.heading}>
            {line.text}
          </Text>
        )
      }
      if (line.kind === 'list') {
        return (
          <Text>
            {line.indent}
            <Text color={COLOR.marker}>{line.marker} </Text>
            {spans(inlineSpans(line.text))}
          </Text>
        )
      }

      return <Text>{spans(inlineSpans(line.text))}</Text>
    })

    return (
      <Box flexDirection="row">
        <Text>{e.props.isFirstOfReply ? '⏺ ' : '  '}</Text>
        <Box flexDirection="column">{rows}</Box>
      </Box>
    )
  })

  on('ui.render', { component: 'ToolUse', props: { tool: 'Bash' } }, async ($, e, next) => {
    const input = e.props.input as { command?: unknown } | null
    const command = typeof input?.command === 'string' ? input.command : null

    if (e.surface !== 'terminal' || e.props.isExpanded || command === null) {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const dot = e.props.isErrored
      ? COLOR.error
      : e.props.isRunning
        ? undefined
        : COLOR.ok
    const [first, ...rest] = command.split('\n')

    return (
      <Box flexDirection="row">
        <Text color={dot} dimColor={e.props.isRunning}>
          {'⏺ '}
        </Text>
        <Text bold>Bash</Text>
        <Text> </Text>
        <Text color={COLOR.command}>{first}</Text>
        {rest.length > 0 ? <Text dimColor> (+{rest.length} lines)</Text> : null}
      </Box>
    )
  })
}
