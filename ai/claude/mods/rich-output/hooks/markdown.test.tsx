import { expect, test } from 'claude-code/testing'

import { classifyLine, inlineSpans, splitBlocks } from './markdown'

const kinds = (line: string) => inlineSpans(line).map(s => s.kind + ':' + s.text)

test('a closed fence is one markdown block', async () => {
  const blocks = splitBlocks('a\n```ts\nx **y**\n```\nb')

  expect(blocks.map(b => b.kind)).toEqual(['line', 'markdown', 'line'])
  expect(blocks[1]).toEqual({ kind: 'markdown', text: '```ts\nx **y**\n```' })
})

test('an unclosed fence runs to the end without throwing', async () => {
  const blocks = splitBlocks('```sh\nls\n# not a heading')

  expect(blocks).toEqual([{ kind: 'markdown', text: '```sh\nls\n# not a heading' }])
})

test('table and quote rows stay markdown', async () => {
  const blocks = splitBlocks('| a | b |\n|---|---|\n> q\ntext')

  expect(blocks.map(b => b.kind)).toEqual(['markdown', 'line'])
})

test('inline spans are classified', async () => {
  expect(kinds('`a` **b** [t](https://x.dev) src/a.ts:12 see https://y.dev')).toEqual([
    'code:a',
    'text: ',
    'bold:b',
    'text: ',
    'link:t',
    'text: ',
    'path:src/a.ts:12',
    'text: see ',
    'link:https://y.dev',
  ])
})

test('unclosed markers stay plain text', async () => {
  expect(kinds('a **b and `c')).toEqual(['text:a **b and `c'])
})

test('bold markers inside inline code are not bold', async () => {
  expect(kinds('`**x**`')).toEqual(['code:**x**'])
})

test('backticked file paths are paths, other backticked text stays code', async () => {
  expect(kinds('`src/a.ts:12` `a.json` `./x/y.sh` `NO_CODE_CHANGE=true` `src/dir` `ls -la`')).toEqual([
    'path:src/a.ts:12',
    'text: ',
    'path:a.json',
    'text: ',
    'path:./x/y.sh',
    'text: ',
    'code:NO_CODE_CHANGE=true',
    'text: ',
    'code:src/dir',
    'text: ',
    'code:ls -la',
  ])
})

test('file names with several dots are one path', async () => {
  expect(kinds('`a.test.tsx` see b.config.json')).toEqual([
    'path:a.test.tsx',
    'text: see ',
    'path:b.config.json',
  ])
})

test('lines are classified as heading, list or plain', async () => {
  expect(classifyLine('## Title')).toEqual({ kind: 'heading', text: 'Title' })
  expect(classifyLine('  - item')).toEqual({ kind: 'list', indent: '  ', marker: '•', text: 'item' })
  expect(classifyLine('2. two')).toEqual({ kind: 'list', indent: '', marker: '2.', text: 'two' })
  expect(classifyLine('plain')).toEqual({ kind: 'plain', text: 'plain' })
})

const MESSAGE = {
  plugin: 'rich-output',
  component: 'AssistantMessage',
  requestId: 'm1',
  props: { text: '## Head\n- item `code`', isFirstOfReply: true },
} as const

test('the terminal draws colored rows, other surfaces keep the engine drawing', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)

    return <Text>engine</Text>
  })

  const terminal = await $.ui.mount({ ...MESSAGE, surface: 'terminal' })
  expect((await terminal.find({ type: 'Text', text: /Head/ }))?.text).toBe('Head')
  await terminal.unmount()

  const desktop = await $.ui.mount({ ...MESSAGE, surface: 'desktop' })
  expect((await desktop.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  await desktop.unmount()
})
