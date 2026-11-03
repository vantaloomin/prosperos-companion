import assert from 'node:assert/strict'
import { test } from 'node:test'
import { accountName, accountValue, isUsual, folderExample, folderShown, sameAccount, signInStep, startingAccount, type CliAccount } from '../../src/features/settings/models/cliAccounts.ts'

const usual: CliAccount = { provider: 'claude_code', account_dir: '', commands: ['claude'], sources: [], signed_in: true, email: 'one@example.com' }
const second: CliAccount = { provider: 'claude_code', account_dir: 'C:\\Users\\Jim\\.claude-account2', commands: ['claude2'], sources: [], signed_in: false, email: '' }
const folderOnly: CliAccount = { provider: 'codex', account_dir: '/home/jim/.codex-work', commands: [], sources: [], signed_in: false, email: '' }

test('each account is named by its command, else its folder, with the email the CLI reports or whether it is signed in', () => {
  assert.equal(accountName(usual), 'claude')
  assert.ok(isUsual(usual) && !isUsual(second))
  assert.equal(accountName(second), 'claude2')
  assert.equal(accountName(folderOnly), '.codex-work')
  assert.equal(accountValue(usual), 'one@example.com')
  assert.equal(accountValue(second), 'Not signed in')
  assert.equal(accountValue({ ...folderOnly, signed_in: true }), 'Signed in')
})

test('a typed folder matches its account whatever its slashes, case or trailing slash', () => {
  assert.ok(sameAccount(second, 'c:/users/jim/.claude-account2/'))
  assert.ok(sameAccount(usual, undefined) && sameAccount(usual, '  '))
  assert.ok(!sameAccount(usual, second.account_dir))
})

test('signing in uses the account’s own command, else the CLI with its folder set', () => {
  assert.equal(signInStep(second, true), 'claude2')
  assert.equal(signInStep({ ...folderOnly, commands: ['codex2'] }, false), 'codex2 login')
  assert.equal(signInStep(folderOnly, false), 'CODEX_HOME="/home/jim/.codex-work" codex login')
  assert.equal(signInStep({ ...second, commands: [] }, true), '$env:CLAUDE_CONFIG_DIR="C:\\Users\\Jim\\.claude-account2"; claude')
  assert.equal(signInStep(usual, true), 'claude')
})

test('a new profile starts on the usual account when it is signed in, else on a signed-in one', () => {
  const signedSecond = { ...second, signed_in: true }
  assert.equal(startingAccount([usual, signedSecond]), usual)
  assert.equal(startingAccount([{ ...usual, signed_in: false }, signedSecond]), signedSecond)
  assert.equal(startingAccount([{ ...usual, signed_in: false }, second])?.account_dir, '')
  assert.equal(startingAccount([signedSecond]), signedSecond)
  assert.equal(startingAccount([]), undefined)
})

test('a folder typed with ~ is the same account, and the example suits the computer', () => {
  const work: CliAccount = { ...folderOnly, account_dir: '/home/jim/.codex-work' }
  assert.ok(sameAccount(work, '~/.codex-work'))
  assert.ok(sameAccount(second, '~\\.claude-account2'))
  assert.equal(folderExample('claude', true), 'C:\\Users\\you\\.claude-second')
  assert.equal(folderExample('codex', false), '~/.codex-second')
})

test('the typed folder is plain with nothing to pick, open while it matches none, and closes once a found account is picked', () => {
  assert.equal(folderShown(false, 3, false), 'plain')
  assert.equal(folderShown(true, 0, false), 'plain')
  const accounts = [usual, second]
  const typed = '/somewhere/else'
  assert.equal(folderShown(true, accounts.length, accounts.some(account => sameAccount(account, typed))), 'open')
  assert.equal(folderShown(true, accounts.length, accounts.some(account => sameAccount(account, second.account_dir))), 'closed')
})

test('profile budgets: presets keep a saved value, and the fold sums them up', async () => {
  const { contextChoices, timeChoices, replyRange, shortTokens, generationSummary } = await import('../../src/features/settings/models/budgets.ts')
  assert.equal(shortTokens(16000), '16K')
  assert.equal(shortTokens(1000000), '1M')
  assert.ok(contextChoices(16000).some(choice => choice.value === 16000))
  assert.ok(contextChoices(16384, 262144).some(choice => choice.label.includes('reported')))
  assert.equal(contextChoices(16384).length, 8)
  assert.deepEqual(timeChoices(180).map(choice => choice.label), ['1 min', '2 min', '3 min', '5 min', '10 min'])
  assert.ok(timeChoices(45).some(choice => choice.label === '45 s'))
  assert.deepEqual(replyRange(800), { min: 200, max: 8000, step: 100 })
  assert.equal(replyRange(16000).max, 16000)
  assert.equal(generationSummary({ context_tokens: 16000, max_output_tokens: 800 } as never), '16K context · 800 reply')
  assert.equal(generationSummary({ context_tokens: 16000, max_output_tokens: 800, reasoning_effort: 'high' } as never), '16K context · 800 reply · High effort')
})
