import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../../api'
import type { TownPaper } from '../../types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { storyDate } from './storyText'

/** The town paper: what happened around the companion's city last week and what's coming up, out every Sunday.
 * Written from the world's own record, so it reads the same each time. */
export function Paper() {
  const [day, setDay] = useState<string | null>(null)
  const issue = useQuery({
    queryKey: ['paper', day],
    queryFn: () => api<TownPaper>(day ? `/life/paper?day=${day}` : '/life/paper'),
    placeholderData: (previous) => previous,
  })
  if (issue.isError) return <section className="today-section"><ErrorNotice error={issue.error} /></section>
  if (!issue.data) return null
  const paper = issue.data
  const headlines = [...paper.news, ...paper.townsfolk]
  const ahead = [...paper.ahead.holidays.map((item) => ({ date: item.date, text: item.name })),
    ...paper.ahead.events.map((item) => ({ date: item.date, text: `${item.name}. ${item.text}` }))]
    .sort((a, b) => a.date.localeCompare(b.date))
  return (
    <section className="today-section paper" aria-labelledby="paper-heading">
      <h2 id="paper-heading">{paper.title}</h2>
      <p className="subtle">
        <button type="button" className="text-button" onClick={() => setDay(paper.previous)} aria-label="Previous issue"><ChevronLeft aria-hidden="true" /></button>
        Out <time dateTime={paper.date}>{storyDate(paper.date)}</time>
        {paper.next && <button type="button" className="text-button" onClick={() => setDay(paper.next)} aria-label="Next issue"><ChevronRight aria-hidden="true" /></button>}
      </p>
      {headlines.length > 0
        ? <ul className="plain-list">{headlines.map((item) => <li key={'id' in item ? item.id : item.key}><strong>{item.headline}</strong> {item.text}</li>)}</ul>
        : <p className="subtle">A quiet week in {paper.city}.</p>}
      {paper.seen.length > 0 && <>
        <h3>Seen around town</h3>
        <ul className="plain-list">{paper.seen.map((item) => <li key={item.companion_id}>{item.text}</li>)}</ul>
      </>}
      {paper.gossip.length > 0 && <>
        <h3>Overheard</h3>
        <ul className="plain-list">{paper.gossip.map((item) => <li key={item.text}>{item.text}</li>)}</ul>
      </>}
      {(ahead.length > 0 || paper.ahead.weather) && <>
        <h3>Coming up</h3>
        <ul className="plain-list">
          {ahead.map((item) => <li key={item.date + item.text}><time dateTime={item.date}>{storyDate(item.date)}</time> {item.text}</li>)}
          {paper.ahead.weather && <li>Weather: {paper.ahead.weather}</li>}
        </ul>
      </>}
    </section>
  )
}
