import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock, MapPin, MessageCircle, Users } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CirclePerson, Companion, PairTie } from '../../types'
import { tieText, tieWhy } from '../memories/pairText'
import { usePortrait } from '../conversation/portrait'
import { useChatStyle } from '../conversation/useChatStyle'
import { useLocalTime } from '../conversation/clock'
import { PROFILE_TABS, circleText, handle, profileClass, profileTab, showsCard } from './profileText'

/**
 * The companion's profile: their card, then Messages, Posts and Character as tabs. It takes the chat
 * style's look. Messages keeps its own header, so the card only shows above Posts and Character, with a
 * Message button that goes back to the chat the way a social app's profile does.
 */
export function Profile({ companion, view, go, children }: { companion: Companion; view: View; go: (view: View) => void; children: ReactNode }) {
  const chat = useChatStyle()
  const card = showsCard(view)
  return (
    <div className={`${profileClass(chat.style, chat.retroDark)}${card ? ' with-card' : ''}`}>
      {card ? (
        <div className="profile-scroll">
          <ProfileCard companion={companion} message={() => go('conversation')} />
          <ProfileTabs view={view} go={go} />
          {children}
        </div>
      ) : <>
        <ProfileTabs view={view} go={go} />
        {children}
      </>}
    </div>
  )
}

function ProfileTabs({ view, go }: { view: View; go: (view: View) => void }) {
  const current = profileTab(view)
  return (
    <nav className="profile-tabs" aria-label="Profile">
      {PROFILE_TABS.map((tab) => (
        <button key={tab.id} type="button" aria-current={current === tab.id ? 'page' : undefined} onClick={() => go(tab.id)}>{tab.label}</button>
      ))}
    </nav>
  )
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
        </div>
        <button type="button" className="button primary profile-message" aria-label="Message" onClick={message}><MessageCircle aria-hidden="true" /><span>Message</span></button>
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
        <li key={tie.companion_id} title={[tie.how, tieWhy(tie)].filter(Boolean).join(' · ') || undefined}>
          {tieText(name, tie)}{tie.how && <span className="subtle"> · {tie.how}</span>}
        </li>
      ))}
    </ul>
  )
}

/** Where they live, their time of day and how many people are in their life; never whether they are free. */
function ProfileFacts({ companion }: { companion: Companion }) {
  const { location, home_city: homeCity, timezone } = companion.version.definition
  const time = useLocalTime(timezone)
  const circle = useQuery({ queryKey: ['circle', false], queryFn: () => api<CirclePerson[]>('/life/circle?include_removed=false') })
  const people = circle.data?.filter((person) => person.status === 'active').length ?? 0
  const place = location || homeCity
  return (
    <ul className="profile-facts">
      {place && <li><MapPin aria-hidden="true" />{place}</li>}
      {time && <li><Clock aria-hidden="true" />{time} for {companion.version.name}</li>}
      {people > 0 && <li><Users aria-hidden="true" />{circleText(people)}</li>}
    </ul>
  )
}
