import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock, MapPin, Users } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CirclePerson, Companion } from '../../types'
import { usePortrait } from '../conversation/portrait'
import { useChatStyle } from '../conversation/useChatStyle'
import { useLocalTime } from '../conversation/clock'
import { PROFILE_TABS, circleText, handle, profileClass, profileTab, showsCard } from './profileText'

/**
 * The companion's profile: their card, then Messages, Posts and Character as tabs. It takes the chat
 * style's look. Messages keeps its own header, so the card only shows above Posts and Character.
 */
export function Profile({ companion, view, go, children }: { companion: Companion; view: View; go: (view: View) => void; children: ReactNode }) {
  const chat = useChatStyle()
  const card = showsCard(view)
  return (
    <div className={`${profileClass(chat.style, chat.retroDark)}${card ? ' with-card' : ''}`}>
      {card ? (
        <div className="profile-scroll">
          <ProfileCard companion={companion} />
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

function ProfileCard({ companion }: { companion: Companion }) {
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
      </div>
      {identity.trim() && <p className="profile-bio">{identity.trim()}</p>}
      <ProfileFacts companion={companion} />
      {interests.length > 0 && (
        <ul className="profile-interests" aria-label="Interests">
          {interests.slice(0, 8).map((interest) => <li key={interest}>{interest}</li>)}
        </ul>
      )}
    </header>
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
