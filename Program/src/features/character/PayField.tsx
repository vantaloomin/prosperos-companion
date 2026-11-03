import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CharacterDefinition } from '../../types'
import { Field } from '../../components/Fields'
import { payDraft, payPlaceholder, payText, readPay } from './money'
import { useSettled } from './useSettled'

interface WorkedOut { monthly: number; text: string; currency: { code: string; symbol: string; name: string }; prefix: boolean }

/** What their work and city pay a month before any pay the user set (companion/life/money.py `worked_out_pay`). */
function useWorkedOut(definition: CharacterDefinition) {
  const { name, identity, background, routine, appearance, personality, home_city: homeCity, money } = useSettled(definition)
  const body = { name, identity, background, routine, appearance, personality, money: { ...money, pay: null } }
  return useQuery({
    queryKey: ['worked-out-pay', homeCity, body], enabled: homeCity !== '',
    queryFn: () => api<WorkedOut | null>(`/world/cities/${encodeURIComponent(homeCity)}/pay`, body),
    staleTime: Infinity, placeholderData: (previous) => previous,
  })
}

/** Pay, always shown (Iris): empty shows what their work pays as its placeholder and leaves it to the app; a number
 * is what they take home a month, 0 unpaid. The money's symbol or name sits inside the box. */
export function PayField({ definition, onChange }: { definition: CharacterDefinition; onChange: (pay: number | null) => void }) {
  const worked = useWorkedOut(definition).data ?? undefined
  const pay = definition.money.pay ?? null
  const [draft, setDraft] = useState(payText(pay))
  // Pay changed elsewhere (a new job from life clears it): the box follows, keeping what is being typed otherwise.
  const [shown, setShown] = useState(pay)
  if (shown !== pay) {
    setShown(pay)
    if (readPay(draft) !== pay) setDraft(payText(pay))
  }
  const unit = worked ? (worked.prefix ? worked.currency.symbol : worked.currency.name) : ''
  return (
    <Field label="Pay" hint="What they take home a month. Left empty, it comes from their work and city.">
      {(id, hint) => (
        <span className={['affix-input', unit && (worked?.prefix ? 'has-prefix' : 'has-suffix')].filter(Boolean).join(' ')}>
          {worked?.prefix && <span className="affix" aria-hidden="true">{unit}</span>}
          <input id={id} type="text" inputMode="numeric" autoComplete="off" value={draft} aria-describedby={hint}
            placeholder={payPlaceholder(worked?.monthly, Boolean(worked && !worked.prefix))}
            onChange={(event) => { const text = payDraft(event.target.value); setDraft(text); setShown(readPay(text)); onChange(readPay(text)) }}
            onBlur={() => setDraft(payText(readPay(draft)))} />
          {worked && !worked.prefix && <span className="affix" aria-hidden="true">{unit}</span>}
        </span>
      )}
    </Field>
  )
}
