import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '../../api'
import type { Secret, SecretsData } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { TextArea, TextInput } from '../../components/Fields'
import { SECRETS_KEY } from './groupState'
import { canForget, formFrom, formBody, howText, keptLine, slipText, type SecretForm as Form } from './secretText'

type Companion = SecretsData['companions'][number]
type Change = (request: () => Promise<unknown>) => Promise<void>

/** Secrets: what only some of them know. Group replies come only from what each speaker knows, and a knower's
 * reply is checked while someone it's kept from is there (companion/secrets.py). */
export function Secrets() {
  const client = useQueryClient()
  const data = useQuery({ queryKey: SECRETS_KEY, queryFn: () => api<SecretsData>('/secrets') })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const change: Change = async (request) => {
    setError('')
    try { client.setQueryData(SECRETS_KEY, await request()) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') }
  }
  const companions = data.data?.companions ?? []
  return (
    <section className="secrets" aria-labelledby="secrets-heading">
      <h2 id="secrets-heading">Secrets</h2>
      <p className="subtle">Someone only knows a secret if they were told, were there when it came out, or you let them find out. Nobody else ever has it in mind.</p>
      {data.isPending && <Loading label="Loading secrets" />}
      {data.isError && <ErrorNotice error={data.error} />}
      {data.isSuccess && <SecretList data={data.data} onChange={change} />}
      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="button" className="button" disabled={!companions.length} onClick={() => setCreating(true)}><Plus aria-hidden="true" />New secret</button>
      </div>
      {creating && <SecretDialog companions={companions} onChange={change} onClose={() => setCreating(false)} />}
    </section>
  )
}

function SecretList({ data, onChange }: { data: SecretsData; onChange: Change }) {
  return <>
    <p className="subtle">{slipText(data.slips)}</p>
    {data.secrets.length
      ? <ul>{data.secrets.map((secret) => <SecretRow key={secret.id} secret={secret} companions={data.companions} onChange={onChange} />)}</ul>
      : <p className="subtle">No secrets yet.</p>}
  </>
}

function SecretRow({ secret, companions, onChange }: { secret: Secret; companions: Companion[]; onChange: Change }) {
  const [editing, setEditing] = useState(false)
  const [ending, setEnding] = useState(false)
  const unaware = companions.filter((companion) => !secret.knows.some((holder) => holder.companion_id === companion.id))
  return (
    <li className="secret">
      <p className="secret-statement"><strong>{secret.statement}</strong> <span className="subtle">· {secret.source}</span></p>
      <p className="subtle">{keptLine(secret)}. Who knows it besides you:</p>
      <ul className="secret-knowers" aria-label="Who knows it">
        {secret.knows.map((holder) => (
          <li key={holder.key}>
            <span>{holder.name} <span className="subtle">({howText(holder)})</span></span>
            {canForget(secret, holder) && <button type="button" className="text-button" onClick={() => void onChange(() => api(`/secrets/${secret.id}/forget`, { companion_id: holder.companion_id }))}>Make them forget</button>}
          </li>
        ))}
      </ul>
      <div className="form-actions">
        <Reveal secret={secret} unaware={unaware} onChange={onChange} />
        <button type="button" className="text-button" onClick={() => setEditing(true)}>Edit</button>
        <button type="button" className="text-button danger" onClick={() => setEnding(true)}>{secret.kind === 'declared' ? 'Delete…' : 'Not a secret anymore…'}</button>
      </div>
      {editing && <SecretDialog secret={secret} companions={companions} onChange={onChange} onClose={() => setEditing(false)} />}
      {ending && <EndDialog secret={secret} onChange={onChange} onClose={() => setEnding(false)} />}
    </li>
  )
}

/** Let them find out: pick someone who doesn't know yet. */
function Reveal({ secret, unaware, onChange }: { secret: Secret; unaware: Companion[]; onChange: Change }) {
  const [who, setWho] = useState('')
  if (!unaware.length) return null
  const chosen = unaware.some((companion) => companion.id === who) ? who : unaware[0].id
  return (
    <span className="secret-reveal">
      <select aria-label="Who finds out" value={chosen} onChange={(event) => setWho(event.target.value)}>
        {unaware.map((companion) => <option key={companion.id} value={companion.id}>{companion.name}</option>)}
      </select>
      <button type="button" className="text-button" onClick={() => void onChange(() => api(`/secrets/${secret.id}/reveal`, { companion_id: chosen }))}>Let them find out</button>
    </span>
  )
}

function EndDialog({ secret, onChange, onClose }: { secret: Secret; onChange: Change; onClose: () => void }) {
  const own = secret.kind === 'declared'
  return (
    <ConfirmDialog title={own ? 'Delete this secret?' : 'Stop treating this as a secret?'} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" onClick={() => void onChange(() => api(`/secrets/${secret.id}`, undefined, 'DELETE')).then(onClose)}>{own ? 'Delete' : 'Not a secret'}</button>
    </>}>
      <p>{own ? 'Nobody is told anything: it stops being tracked, and replies are no longer checked for it.' : 'It stays part of their life, but replies are no longer checked for it.'}</p>
    </ConfirmDialog>
  )
}

/** A new secret, or a change to one. Words from a storyline or a description stay as they are there. */
function SecretDialog({ secret, companions, onChange, onClose }: { secret?: Secret; companions: Companion[]; onChange: Change; onClose: () => void }) {
  const [form, setForm] = useState<Form>(() => formFrom(secret))
  const set = (change: Partial<Form>) => setForm((current) => ({ ...current, ...change }))
  const own = !secret || secret.kind === 'declared'
  const ready = !own || (form.statement.trim() && form.knows.length > 0)
  const save = () => void onChange(() => secret ? api(`/secrets/${secret.id}`, formBody(form, own), 'PATCH') : api('/secrets', formBody(form, own))).then(onClose)
  return (
    <ConfirmDialog title={secret ? 'Edit the secret' : 'New secret'} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" disabled={!ready} onClick={save}>Save</button>
    </>}>
      <div className="secret-form">
        {own ? <OwnFields form={form} companions={companions} set={set} /> : <p>{secret.statement} <span className="subtle">({secret.source}; change it there.)</span></p>}
        <KeptFields form={form} companions={companions} set={set} />
        <TextInput label="Words that give it away (optional)" value={form.words} maxLength={400} placeholder="seeing each other, dating, kissed"
          hint={secret && !secret.own_key_words.length ? `Now: ${secret.key_words.join(', ') || 'none'}. Leave empty to use the secret's own words.` : 'Separated by commas. Leave empty to use the secret\'s own words.'}
          onChange={(words) => set({ words })} />
      </div>
    </ConfirmDialog>
  )
}

const toggle = (list: string[], id: string) => list.includes(id) ? list.filter((item) => item !== id) : [...list, id]

function OwnFields({ form, companions, set }: { form: Form; companions: Companion[]; set: (change: Partial<Form>) => void }) {
  return <>
    <TextArea label="The secret" value={form.statement} maxLength={400} rows={2} placeholder="Billy and Katie have been secretly seeing each other" onChange={(statement) => set({ statement })} />
    <TextInput label="Who it's about" value={form.about} maxLength={300} placeholder="Billy, Katie" hint="Names, separated by commas. A companion's name links to them." onChange={(about) => set({ about })} />
    <fieldset className="group-picker">
      <legend>Who knows it</legend>
      {companions.map((companion) => <label key={companion.id} className="check-row"><input type="checkbox" checked={form.knows.includes(companion.id)} onChange={() => set({ knows: toggle(form.knows, companion.id) })} />{companion.name}</label>)}
    </fieldset>
  </>
}

function KeptFields({ form, companions, set }: { form: Form; companions: Companion[]; set: (change: Partial<Form>) => void }) {
  return (
    <fieldset className="group-picker">
      <legend>Who must not find out</legend>
      <label className="check-row"><input type="checkbox" checked={form.everyone} onChange={() => set({ everyone: !form.everyone })} />Everyone who doesn&apos;t know it</label>
      {!form.everyone && companions.filter((companion) => !form.knows.includes(companion.id)).map((companion) => (
        <label key={companion.id} className="check-row"><input type="checkbox" checked={form.kept.includes(companion.id)} onChange={() => set({ kept: toggle(form.kept, companion.id) })} />{companion.name}</label>
      ))}
    </fieldset>
  )
}
