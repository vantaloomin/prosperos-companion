import { useEffect, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Clock, CloudRain, MapPin, MessageCircle, Undo2, Users } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CirclePerson, Companion, PairTie } from '../../types'
import { howText, listedHow, tieText, tieWhy } from '../memories/pairText'
import { usePortrait } from '../conversation/portrait'
import { useChatStyle } from '../conversation/useChatStyle'
import { useLocalTime } from '../conversation/clock'
import { StatusEditor } from '../status/StatusLine'
import { profileTabs, circleText, handle, placeFact, profileClass, profileTab, showsCard } from './profileText'
import { useEraWords } from '../world/useEraWords'
import { ROUGH_PATCH_KEY, UNDO_MS, roughPatchLine, type RoughPatch } from './roughPatchText'

/**
 * The companion's profile: Messages, Posts and Character as tabs, then their card. It takes the chat
 * style's look. The tabs stay at the top on every tab and never scroll away. Messages keeps its own header,
 * so the card only shows on Posts and Character, scrolling with the page, with a Message button that goes
 * back to the chat the way a social app's profile does.
 */
export function Profile({ companion, view, go, children }: { companion: Companion; view: View; go: (view: View) => void; children: ReactNode }) {
  const chat = useChatStyle()
  const card = showsCard(view)
  return (
    <div className={`${profileClass(chat.style, chat.retroDark)}${card ? ' with-card' : ''}`}>
      <ProfileTabs view={view} go={go} />
      {card ? (
        <div className="profile-scroll">
          <ProfileCard companion={companion} message={() => go('conversation')} />
          {children}
        </div>
      ) : children}
    </div>
  )
}

function ProfileTabs({ view, go }: { view: View; go: (view: View) => void }) {
  const current = profileTab(view)
  const words = useEraWords()
  return (
    <nav className="profile-tabs" aria-label="Profile">
      {profileTabs(words).map((tab) => (
        <button key={tab.id} type="button" aria-current={current === tab.id ? 'page' : undefined} onClick={() => go(tab.id)}>{tab.label}</button>
      ))}
    </nav>
  )
}

/** Message, or "Write" in Camelot (the era's words, eraWords.ts). */
function MessageButton({ onClick }: { onClick: () => void }) {
  const label = useEraWords().message_button
  return <button type="button" className="button primary profile-message" aria-label={label} onClick={onClick}><MessageCircle aria-hidden="true" /><span>{label}</span></button>
}

function ProfileCard({ companion, message }: { companion: Companion; message: () => void }) {
  const { identity, interests } = companion.version.definition
  const name = companion.version.name
  const portrait = usePortrait()
  return (
    <header className="profile-card">
      <div className="profile-titlebar" aria-hidden="true">{name} · Profile</div>
      <div className="profile-cover" aria-hidden="true" />
      <div className="profile-who">
        {portrait ? <img className="profile-avatar" src={portrait} alt="" /> : <div className="profile-avatar" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>}
        <div className="profile-name">
          <h1>{name}</h1>
          {handle(name) && <p className="profile-handle">{handle(name)}</p>}
          <StatusEditor id={companion.id} name={name} status={companion.status} />
        </div>
        <MessageButton onClick={message} />
      </div>
      {identity.trim() && <p className="profile-bio">{identity.trim()}</p>}
      <ProfileFacts companion={companion} />
      <ProfileTies name={name} />
      {interests.length > 0 && (
        <ul className="profile-interests" aria-label="Interests">
          {interests.slice(0, 8).map((interest) => <li key={interest}>{interest}</li>)}
        </ul>
      )}
    </header>
  )
}

/** How close they and the other companions they know feel. Read-only: only what happens between them moves it. */
function ProfileTies({ name }: { name: string }) {
  const ties = useQuery({ queryKey: ['companion-ties'], queryFn: () => api<{ ties: PairTie[] }>('/companion/ties') })
  if (!ties.data?.ties.length) return null
  return (
    <ul className="profile-facts profile-ties" aria-label={`${name} and your other companions`}>
      {ties.data.ties.map((tie) => (
        <li key={tie.companion_id} title={[howText(tie.how), tieWhy(tie)].filter(Boolean).join(' · ') || undefined}>
          {tieText(name, tie)}{tie.how && <span className="subtle"> · {listedHow(tie.how)}</span>}
        </li>
      ))}
    </ul>
  )
}

/** Where they live (and how far from you, when it is another city), their time of day and how many people are in their life. Their status above may say they are
 * away, as an away message would; nothing here says whether they are online. */
function ProfileFacts({ companion }: { companion: Companion }) {
  const { location, home_city: homeCity, timezone } = companion.version.definition
  const time = useLocalTime(timezone)
  const circle = useQuery({ queryKey: ['circle', false], queryFn: () => api<CirclePerson[]>('/life/circle?include_removed=false') })
  const people = circle.data?.filter((person) => person.status === 'active').length ?? 0
  const place = placeFact(location || homeCity, companion.status?.where)
  return (
    <ul className="profile-facts">
      {place && <li><MapPin aria-hidden="true" />{place}</li>}
      {time && <li><Clock aria-hidden="true" />{time} for {companion.version.name}</li>}
      {people > 0 && <li><Users aria-hidden="true" />{circleText(people)}</li>}
      <RoughPatchFact />
    </ul>
  )
}

/** "Things are a bit tense" while a rough patch is open (companion/life/rough_patches.py). With Hidden values > moods
 * on it also says what it is over, on a line of its own, and Let it go clears the air, with a short Undo after. */
function RoughPatchFact() {
  const client = useQueryClient()
  const patch = useQuery({ queryKey: ROUGH_PATCH_KEY, queryFn: () => api<RoughPatch>('/life/rough-patch') })
  const [letGo, setLetGo] = useState<string | null>(null)
  useEffect(() => {
    if (!letGo) return
    const timer = window.setTimeout(() => setLetGo(null), UNDO_MS)
    return () => window.clearTimeout(timer)
  }, [letGo])
  const act = async (id: string, action: 'let-go' | 'undo') => {
    client.setQueryData(ROUGH_PATCH_KEY, await api<RoughPatch>(`/life/rough-patch/${id}/${action}`, {}))
    setLetGo(action === 'let-go' ? id : null)
  }
  if (letGo) return (
    <li className="profile-patch" role="status" aria-live="polite">
      <span>You let it go.</span>
      <button type="button" className="text-button" onClick={() => void act(letGo, 'undo')}><Undo2 aria-hidden="true" />Undo</button>
    </li>
  )
  const line = roughPatchLine(patch.data)
  if (!line || !patch.data) return null
  const { id, about, small } = patch.data
  return (
    <li className={about ? 'profile-patch has-reason' : 'profile-patch'}>
      <span className="profile-patch-text"><CloudRain aria-hidden="true" />{line}</span>
      {about && id && !small && <button type="button" className="text-button" onClick={() => void act(id, 'let-go')}><Check aria-hidden="true" />Let it go</button>}
    </li>
  )
}
