import { expect, test } from 'claude-code/testing'

import { commandSpans } from './bash'

const kinds = (command: string) =>
  commandSpans(command)
    .filter(s => s.kind !== 'text' || s.text.trim() !== '')
    .map(s => s.kind + ':' + s.text)

test('program, option, path and plain argument are told apart', async () => {
  expect(kinds('python3 tests/run_tests.py --paths a.py -v now')).toEqual([
    'program:python3',
    'path:tests/run_tests.py',
    'option:--paths',
    'text:a.py',
    'option:-v',
    'text:now',
  ])
})

test('a quoted string is one span even with spaces and dashes inside', async () => {
  expect(kinds('git commit -m "fix: a -b c" \'x y\'')).toEqual([
    'program:git',
    'text:commit',
    'option:-m',
    'string:"fix: a -b c"',
    "string:'x y'",
  ])
})

test('operators end a command and the next word is a program again', async () => {
  expect(kinds('cd ~/x && ls -la | grep a; echo $HOME 2>&1')).toEqual([
    'program:cd',
    'path:~/x',
    'operator:&&',
    'program:ls',
    'option:-la',
    'operator:|',
    'program:grep',
    'text:a',
    'operator:;',
    'program:echo',
    'var:$HOME',
    'operator:2>&1',
  ])
})

test('leading assignments are vars and the program follows', async () => {
  expect(kinds('FOO=1 BAR=x make all')).toEqual(['var:FOO=1', 'var:BAR=x', 'program:make', 'text:all'])
})

test('a redirect keeps the program position', async () => {
  expect(kinds('echo hi > out.txt')).toEqual(['program:echo', 'text:hi', 'operator:>', 'text:out.txt'])
})

test('an unclosed quote runs to the end without throwing', async () => {
  expect(kinds('echo "abc def')).toEqual(['program:echo', 'string:"abc def'])
})

test('the spans always join back to the original command', async () => {
  for (const command of ['a  b\t-c', 'x && y || z', 'echo "a\\"b" \'c\'', 'cat <f >g 2>&1', 'echo \\; x', '']) {
    expect(
      commandSpans(command)
        .map(s => s.text)
        .join(''),
    ).toBe(command)
  }
})
