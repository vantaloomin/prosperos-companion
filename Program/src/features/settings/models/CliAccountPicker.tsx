// Settings > Models: pick which Claude or ChatGPT account a Claude Code or Codex profile uses, from the accounts
// found on this PC (companion/providers/cli_accounts.py). Ported from prosperos-dungeon at 6ac621f; looking can be
// turned off here, and a new profile starts on a signed-in account by itself.
import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '../../../api'
import { SETTINGS_KEY } from '../../../companion'
import { Notice } from '../../../components/Feedback'
import { Toggle } from '../../../components/Fields'
import { shownPath } from '../../../paths'
import type { WorkspaceSettings } from '../../../types'
import { accountLabel, sameAccount, signInStep, startingAccount, type CliAccount } from './cliAccounts'
import type { Provider } from './types'

const WINDOWS = typeof navigator !== 'undefined' && /win/i.test(navigator.platform)
const KEY = ['cli-accounts']
interface Found { enabled: boolean; accounts: CliAccount[] }

/** `fresh` is a new profile: it moves to a signed-in account by itself when the usual one is not signed in. */
export function CliAccountPicker({ provider, value, fresh, onPick }: { provider: Provider; value?: string; fresh: boolean; onPick: (folder: string) => void }) {
  // Each account's sign-in is asked of its CLI, which takes a moment, so the list is kept while Settings is open.
  const query = useQuery({ queryKey: KEY, queryFn: () => api<Found>('/models/cli-accounts'), staleTime: 5 * 60_000 })
  const mine = accountsFor(query.data, provider)
  useStartingAccount(fresh && !value?.trim(), mine, onPick)
  if (!query.data && !query.isError) return <p className="subtle">Looking for accounts on this computer…</p>
  const enabled = query.data?.enabled ?? true
  return <div className="cli-accounts form-stack">
    {enabled && <AccountList provider={provider} accounts={mine ?? []} value={value} busy={query.isFetching} onPick={onPick} onLook={() => void query.refetch()} />}
    <LookSwitch enabled={enabled} />
  </div>
}

const accountsFor = (found: Found | undefined, provider: Provider) => found ? found.accounts.filter(account => account.provider === provider) : null

function useStartingAccount(open: boolean, accounts: CliAccount[] | null, onPick: (folder: string) => void) {
  const done = useRef(false)
  useEffect(() => {
    if (done.current || !open || !accounts) return
    done.current = true
    const start = startingAccount(accounts)
    if (start?.account_dir) onPick(start.account_dir)
  }, [open, accounts, onPick])
}

function AccountList({ provider, accounts, value, busy, onPick, onLook }: { provider: Provider; accounts: CliAccount[]; value?: string; busy: boolean; onPick: (folder: string) => void; onLook: () => void }) {
  const chosen = accounts.find(account => sameAccount(account, value))
  const again = <button type="button" className="button" disabled={busy} onClick={onLook}><RefreshCw size={15} aria-hidden="true" />{busy ? 'Looking…' : 'Look again'}</button>
  if (!accounts.length) return <div className="form-actions"><span className="subtle">No {provider === 'codex' ? 'Codex' : 'Claude Code'} accounts found on this computer.</span>{again}</div>
  return <>
    <fieldset className="provider-picker cli-account-list"><legend>Account</legend>
      {accounts.map(account => <button key={account.account_dir || 'usual'} type="button" className={`button${account === chosen ? ' selected' : ''}`} aria-pressed={account === chosen}
        title={account.account_dir ? shownPath(account.account_dir) : undefined} onClick={() => onPick(account.account_dir)}>{accountLabel(account)}{account.signed_in ? '' : ' (not signed in)'}</button>)}
      {again}
    </fieldset>
    <AccountNote chosen={chosen} />
  </>
}

function AccountNote({ chosen }: { chosen?: CliAccount }) {
  if (!chosen) return <p className="subtle">Found from your claude and codex commands (such as claude2), your PowerShell profile and account folders. Pick one, or type a folder below.</p>
  if (!chosen.signed_in) return <p className="subtle">This account is not signed in. Run <code>{signInStep(chosen, WINDOWS)}</code> in a terminal and sign in, then look again.</p>
  return <p className="subtle">{chosen.account_dir ? `Uses the account kept in ${shownPath(chosen.account_dir)}.` : 'Uses the account the CLI is usually signed in to.'}</p>
}

/** On unless turned off: off, nothing is looked for and only a typed folder is used. */
function LookSwitch({ enabled }: { enabled: boolean }) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const save = async (find_cli_accounts: boolean) => {
    setError('')
    try {
      client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', { find_cli_accounts }, 'PUT'))
      await client.invalidateQueries({ queryKey: KEY })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  return <>
    <Toggle label="Look for accounts on this computer" checked={enabled} onChange={checked => void save(checked)}
      hint="Reads your claude and codex commands and account folder names to list your accounts. Sign-ins stay with the CLI and are never opened." />
    {error && <Notice tone="error">{error}</Notice>}
  </>
}
