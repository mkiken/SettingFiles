import type { Register } from 'claude-code'

import { commandSpans } from './bash'
import { classifyLine, inlineSpans, splitBlocks } from './markdown'
import type { Span } from './markdown'

// Mariana palette as hex: color names are drawn as the engine's own vivid colors.
const COLOR = {
  heading: '#d8b6d8',
  code: '#c695c6',
  path: '#5fb4b4',
  link: '#85add6',
  bold: '#f9ae58',
  marker: '#8fa1b3',
  ok: '#99c794',
  error: '#ec5f66',
} as const

// Shell words of the Bash row, by role.
const COMMAND_COLOR = {
  program: '#85add6',
  option: '#f9ae58',
  string: '#99c794',
  path: '#5fb4b4',
  var: '#c695c6',
} as const

export const register: Register = on => {
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.isSummary) return next(e)

    const { Box, Text, Markdown } = $.ui.resolve(e)

    const spans = (items: Span[]) =>
      items.map(s => {
        switch (s.kind) {
          case 'bold':
            return (
              <Text bold color={COLOR.bold}>
                {s.text}
              </Text>
            )
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
        <Text>
          {commandSpans(first).map(s =>
            s.kind === 'text' ? (
              s.text
            ) : s.kind === 'operator' ? (
              <Text dimColor>{s.text}</Text>
            ) : (
              <Text color={COMMAND_COLOR[s.kind]}>{s.text}</Text>
            ),
          )}
        </Text>
        {rest.length > 0 ? <Text dimColor> (+{rest.length} lines)</Text> : null}
      </Box>
    )
  })
}
