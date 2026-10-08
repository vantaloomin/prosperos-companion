import { useEffect, useRef, useState } from 'react'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import type { SearchResult, SearchResults } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { snippet } from './search'

const DELAY = 250

function useSettled(value: string) {
  const [settled, setSettled] = useState(value)
  useEffect(() => { const timer = window.setTimeout(() => setSettled(value), DELAY); return () => window.clearTimeout(timer) }, [value])
  return settled
}

interface Props { name: string; onPick: (result: SearchResult) => void; onClose: () => void }

export function ConversationSearch({ name, onPick, onClose }: Props) {
  const [text, setText] = useState('')
  const query = useSettled(text.trim())
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { input.current?.focus() }, [])
  const search = useQuery({
    queryKey: ['conversation-search', query],
    queryFn: () => api<SearchResults>(`/conversation/search?q=${encodeURIComponent(query)}`),
    enabled: query.length >= 2,
    staleTime: 10_000,
  })
  return (
    <div className="conversation-search" role="search" onKeyDown={(event) => { if (event.key === 'Escape') onClose() }}>
      <div className="search-bar">
        <label className="visually-hidden" htmlFor="conversation-search">Search the conversation</label>
        <input id="conversation-search" ref={input} type="search" value={text} placeholder={`Search your conversation with ${name}`} onChange={(event) => setText(event.target.value)} />
        <button type="button" className="icon-button" aria-label="Close search" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <SearchBody query={query} search={search} name={name} onPick={onPick} />
    </div>
  )
}

function SearchBody({ query, search, name, onPick }: { query: string; search: UseQueryResult<SearchResults>; name: string; onPick: (result: SearchResult) => void }) {
  if (query.length < 2) return null
  if (search.isPending) return <Loading label="Searching" />
  if (search.isError) return <ErrorNotice error={search.error} />
  const { results, more } = search.data
  return (
    <div className="search-results">
      <p className="subtle" role="status">{results.length === 0 ? 'Nothing matches that.' : `${results.length}${more ? '+' : ''} ${results.length === 1 ? 'match' : 'matches'}, newest first.`}</p>
      {results.length > 0 && (
        <ul>
          {results.map((result) => <ResultItem key={result.id} result={result} query={query} name={name} onPick={onPick} />)}
        </ul>
      )}
    </div>
  )
}

function ResultItem({ result, query, name, onPick }: { result: SearchResult; query: string; name: string; onPick: (result: SearchResult) => void }) {
  const piece = snippet(result.text, query)
  const when = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(result.created_at))
  return (
    <li>
      <button type="button" className="search-result" onClick={() => onPick(result)}>
        <span className="search-meta"><span className="speaker">{result.role === 'user' ? 'You' : name}</span><time dateTime={result.created_at}>{when}</time></span>
        <span className="search-snippet">{piece.before}{piece.match && <mark>{piece.match}</mark>}{piece.after}</span>
      </button>
    </li>
  )
}
