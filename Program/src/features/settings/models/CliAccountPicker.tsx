// Settings > Models: pick which Claude or ChatGPT account a Claude Code or Codex profile uses, from the accounts
// found on this PC (companion/providers/cli_accounts.py). Ported from prosperos-dungeon at 6ac621f; looking can be
// turned off here, and a new profile starts on a signed-in account by itself.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '../../../api'
import { SETTINGS_KEY } from '../../../companion'
import { Notice } from '../../../components/Feedback'
import { Toggle } from '../../../components/Fields'
import { shownPath } from '../../../paths'
import type { WorkspaceSettings } from '../../../types'
import { type FolderShown, WINDOWS, accountLabel, folderShown, sameAccount, signInStep, startingAccount, type CliAccount } from './cliAccounts'
import type { Provider } from './types'

const KEY = ['cli-accounts']
interface Found { enabled: boolean; accounts: CliAccount[] }
interface PickerProps { provider: Provider; value?: string; fresh: boolean; onPick: (folder: string) => void; children: ReactNode }

/** `fresh` is a new profile: it moves to a signed-in account by itself when the usual one is not signed in.
 * `children` is the typed account folder, kept behind "Type an account folder instead" while a found account is picked. */
export function CliAccountPicker({ provider, value, fresh, onPick, children }: PickerProps) {
  // Each account's sign-in is asked of its CLI, which takes a moment, so the list is kept while Settings is open.
  const query = useQuery({ queryKey: KEY, queryFn: () => api<Found>('/models/cli-accounts'), staleTime: 5 * 60_000 })
  const mine = accountsFor(query.data, provider)
  useStartingAccount(fresh && !value?.trim(), mine, onPick)
  if (!query.data && !query.isError) return <p className="subtle">Looking for accounts on this computer…</p>
  const { enabled, chosen } = picked(query.data, mine, value)
  return <div className="cli-accounts form-stack">
    {enabled && <AccountList provider={provider} accounts={mine ?? []} chosen={chosen} busy={query.isFetching} onPick={onPick} onLook={() => void query.refetch()} />}
    <LookSwitch enabled={enabled} />
    <TypedFolder shown={folderShown(enabled, mine?.length ?? 0, !!chosen)} picked={chosen?.account_dir}>{children}</TypedFolder>
  </div>
}

const picked = (found: Found | undefined, mine: CliAccount[] | null, value?: string) =>
  ({ enabled: found?.enabled ?? true, chosen: mine?.find(account => sameAccount(account, value)) })

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

interface ListProps { provider: Provider; accounts: CliAccount[]; chosen?: CliAccount; busy: boolean; onPick: (folder: string) => void; onLook: () => void }

function AccountList({ provider, accounts, chosen, busy, onPick, onLook }: ListProps) {
  const again = <div className="form-actions"><button type="button" className="button" disabled={busy} onClick={onLook}><RefreshCw size={15} aria-hidden="true" />{busy ? 'Looking…' : 'Look again'}</button></div>
  if (!accounts.length) return <><p className="subtle">No {provider === 'codex' ? 'Codex' : 'Claude Code'} accounts found on this computer.</p>{again}</>
  return <>
    <fieldset className="provider-picker cli-account-list"><legend>Account</legend>
      {accounts.map(account => <button key={account.account_dir || 'usual'} type="button" className={`button${account === chosen ? ' selected' : ''}`} aria-pressed={account === chosen}
        title={account.account_dir ? shownPath(account.account_dir) : undefined} onClick={() => onPick(account.account_dir)}>{accountLabel(account)}{account.signed_in ? '' : ' (not signed in)'}</button>)}
    </fieldset>
    <AccountNote chosen={chosen} />
    {again}
  </>
}

function AccountNote({ chosen }: { chosen?: CliAccount }) {
  if (!chosen) return <p className="subtle">Found from your claude and codex commands (such as claude2), your PowerShell profile and account folders. Pick one, or type a folder below.</p>
  if (!chosen.signed_in) return <Notice>This account is not signed in. Run <code>{signInStep(chosen, WINDOWS)}</code> in a terminal and sign in, then look again.</Notice>
  return <p className="subtle">{chosen.account_dir ? `Uses the account kept in ${shownPath(chosen.account_dir)}.` : 'Uses the account the CLI is usually signed in to.'}</p>
}

/** Plain with no chips to choose from; else a disclosure, closed while a found account is picked until the user
 * opens it. Picking another account closes it again; only clicks on its summary open or close it. */
function TypedFolder({ shown, picked, children }: { shown: FolderShown; picked?: string; children: ReactNode }) {
  const [opened, setOpened] = useState<{ picked?: string; open: boolean }>({ open: false })
  if (shown === 'plain') return <>{children}</>
  const open = shown === 'open' || (opened.open && opened.picked === picked)
  return <details className="typed-folder" open={open}>
    <summary onClick={event => { event.preventDefault(); setOpened({ picked, open: !open }) }}>Type an account folder instead</summary>
    <div className="form-stack">{children}</div>
  </details>
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
      hint="Finds your Claude Code and Codex accounts from their commands and folder names, for every profile. Sign-ins are never opened." />
    {error && <Notice tone="error">{error}</Notice>}
  </>
}
