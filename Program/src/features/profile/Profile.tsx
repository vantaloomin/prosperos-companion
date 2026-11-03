import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronLeft, Clock, CloudRain, MapPin, MessageCircle, Undo2, Users } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CirclePerson, Companion, PairTie } from '../../types'
import { howText, listedHow, tieText, tieWhy } from '../memories/pairText'
import { usePortrait } from '../conversation/portrait'
import { useChatStyle } from '../conversation/useChatStyle'
import { useLocalTime } from '../conversation/clock'
import { useChatLook } from '../conversation/useTheirLook'
import { StatusEditor } from '../status/StatusLine'
import { profileTabs, circleText, handle, showsHandle, placeFact, profileClass, profileTab, showsCard } from './profileText'
import { useEraWords, useEraDecade } from '../world/useEraWords'
import { ROUGH_PATCH_KEY, UNDO_MS, roughPatchLine, type RoughPatch } from './roughPatchText'

/**
 * The companion's profile, opened from their name in the chat: one header (their picture, name, status, where and
 * when they are), then Posts, Memories and Character as tabs. It takes the chat style's look. The header scrolls with
 * the page and the tabs stay at the top; Message goes back to the chat the way a social app's profile does. The pages
 * under a tab (their pictures, Our year) keep only the tabs.
 */
export function Profile({ companion, view, go, children }: { companion: Companion; view: View; go: (view: View) => void; children: ReactNode }) {
  const chat = useChatStyle()
  const card = showsCard(view)
  return (
    <div className={`${profileClass(chat.style, chat.retroDark)}${card ? ' with-card' : ''}`}>
      {card ? (
        <div className="profile-scroll">
          <ProfileCard companion={companion} posts={view === 'feed'} go={go} />
          <ProfileTabs view={view} go={go} />
          {children}
        </div>
      ) : <><ProfileTabs view={view} go={go} />{children}</>}
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

/**
 * Their picture opens Profile pictures. Their name takes their color, as in the chat (theirLook.ts). The bio, ties and
 * interests sit on Posts, the social side of the profile. The cover band went in 1.3, except Visual novel's small stage
 * under their portrait, which is that style's period look. Bubbles and Feed put Message under the place line; the other
 * styles keep it beside the name. A phone gets a ‹ back to the chat.
 */
function ProfileCard({ companion, posts, go }: { companion: Companion; posts: boolean; go: (view: View) => void }) {
  const name = companion.version.name
  const portrait = usePortrait()
  const decade = useEraDecade()
  const style = useChatStyle().style
  const card = useRef<HTMLElement>(null)
  const look = useChatLook(card)
  const below = style === 'bubbles' || style === 'feed'
  const message = <MessageButton onClick={() => go('conversation')} />
  return (
    <header ref={card} className={`profile-card${style === 'novel' ? ' novel-card' : ''}${look.className}`} style={look.style} data-their-font={look.font}>
      <button type="button" className="icon-button profile-back" aria-label="Back to chat" onClick={() => go('conversation')}><ChevronLeft aria-hidden="true" /></button>
      <div className="profile-titlebar" aria-hidden="true">{name} · Profile</div>
      {style === 'novel' && <div className="profile-cover" aria-hidden="true" />}
      <div className="profile-who">
        <button type="button" className="profile-avatar-button" aria-label="Profile pictures" title="Profile pictures" onClick={() => go('portraits')}>
          {portrait ? <img className="profile-avatar" src={portrait} alt="" /> : <span className="profile-avatar" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>}
        </button>
        <div className="profile-name">
          <h1>{name}</h1>
          {showsHandle(decade) && handle(name) && <p className="profile-handle">{handle(name)}</p>}
          <StatusEditor id={companion.id} name={name} status={companion.status} />
        </div>
        {!below && message}
      </div>
      <ProfileFacts companion={companion} />
      {below && <div className="profile-actions">{message}</div>}
      {posts && <ProfileAbout companion={companion} />}
    </header>
  )
}

function ProfileAbout({ companion }: { companion: Companion }) {
  const { identity, interests } = companion.version.definition
  return <>
    {identity.trim() && <p className="profile-bio">{identity.trim()}</p>}
    <ProfileTies name={companion.version.name} />
    {interests.length > 0 && (
      <ul className="profile-interests" aria-label="Interests">
        {interests.slice(0, 8).map((interest) => <li key={interest}>{interest}</li>)}
      </ul>
    )}
  </>
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
      {time && <li><Clock aria-hidden="true" />{time} their time</li>}
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
