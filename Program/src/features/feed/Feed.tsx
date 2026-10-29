import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, newId } from '../../api'
import { HISTORY_KEY, type View } from '../../companion'
import type { Companion, FeedPage, FeedPost, FeedSource } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { PostCard, type PostActions } from './PostCard'
import { ReadBatcher, joinPages, nextReaction } from './feedState'
import { isActive } from './imageState'
import { useEraWords } from '../world/useEraWords'
import type { EraWords } from '../world/eraWords'

export function Feed({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const [hidden, setHidden] = useState(false)
  const [source, setSource] = useState<FeedSource>('all')
  const [error, setError] = useState<string | null>(null)
  const words = useEraWords()
  const key = useMemo(() => ['feed', hidden, source], [hidden, source])
  const feed = useInfiniteQuery({
    queryKey: key,
    queryFn: ({ pageParam }) => api<FeedPage>(`/feed?limit=20&hidden=${hidden}&source=${source}${pageParam ? `&before=${encodeURIComponent(pageParam)}` : ''}`),
    initialPageParam: '',
    getNextPageParam: (last) => last.next_before ?? undefined,
    // While an image is being made, look again every few seconds; while an answer to a comment is on its way, now and then.
    refetchInterval: (query) => {
      const posts = query.state.data?.pages.flatMap((page) => page.posts) ?? []
      if (posts.some((post) => post.image && isActive(post.image.status))) return 3000
      return posts.some((post) => post.thread?.waiting) ? 20000 : false
    },
  })
  const name = companion.version.name
  const posts = joinPages(feed.data?.pages ?? [])
  const unread = useArrivalCount(feed.data?.pages[0]?.unread)

  const batcher = useMemo(() => new ReadBatcher((ids) => {
    void api('/feed/read', { post_ids: ids }).then(() => Promise.all([client.invalidateQueries({ queryKey: ['today'] }), client.invalidateQueries({ queryKey: ['feed'] })])).catch(() => undefined)
  }), [client])
  useEffect(() => () => batcher.flush(), [batcher])

  const replace = (post: FeedPost) => client.setQueryData<{ pages: FeedPage[] }>(key, (current) => current && {
    ...current, pages: current.pages.map((page) => ({ ...page, posts: page.posts.map((item) => item.id === post.id ? post : item) })),
  })
  const run = async (action: () => Promise<unknown>) => {
    try { await action(); setError(null) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  // A reply to a post, or an answer to a question post, goes to chat as a reply to it.
  const sendToChat = async (path: string, body: object) => {
    try {
      await api(path, body)
      await client.invalidateQueries({ queryKey: HISTORY_KEY })
      go('conversation')
      return true
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'The message was not sent.'); return false }
  }
  const actions: PostActions = {
    saw: (post) => batcher.saw(post.id),
    refresh: () => void client.invalidateQueries({ queryKey: ['feed'] }),
    react: (post, reaction) => void run(async () => replace(await api<FeedPost>(`/feed/${post.id}/reaction`, { reaction: nextReaction(post.reaction, reaction) }))),
    hide: (post, hide) => void run(async () => { await api(`/feed/${post.id}/${hide ? 'hide' : 'unhide'}`, {}); await client.invalidateQueries({ queryKey: ['feed'] }) }),
    remove: (post) => void run(async () => { await api(`/feed/${post.id}/remove`, {}); await client.invalidateQueries({ queryKey: ['feed'] }) }),
    discuss: (post, text) => sendToChat(`/feed/${post.id}/discuss?wait=false`, { text, client_id: newId() }),
    openChat: () => go('conversation'),
    comment: async (post, text) => {
      try { replace(await api<FeedPost>(`/feed/${post.id}/comments`, { text })); setError(null); return true } catch (failure) { setError(failure instanceof Error ? failure.message : 'The comment was not posted.'); return false }
    },
    answer: (post, option) => sendToChat(`/feed/${post.id}/answer?wait=false`, { option, client_id: newId() }),
  }

  const exportFeed = async () => run(async () => {
    const data = await api('/feed/export')
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    link.download = `${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-feed.json`
    link.click()
    URL.revokeObjectURL(link.href)
  })

  return (
    <section className="page feed">
      <header className="page-header">
        <div>
          <h2>{words.posts_tab}</h2>
          <p className="subtle">{name}'s {words.posts}, what their friends are up to, and yours{unreadText(unread)}. Nobody outside the app sees them.</p>
        </div>
        <button type="button" className="button" onClick={() => void exportFeed()}><Download aria-hidden="true" />Export</button>
      </header>
      <OwnPost onPosted={() => {
        setError(null)
        // The name and Friends filters leave the user's posts out: show the new one at the top of Everyone.
        if (source === 'companion' || source === 'circle') setSource('all')
        void client.invalidateQueries({ queryKey: ['feed'] })
      }} onError={setError} />
      <div className="memory-toolbar">
        <SourcePicker source={source} name={name} onChange={setSource} />
        <Toggle label={`Show hidden ${words.posts}`} checked={hidden} onChange={setHidden} />
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      <FeedStatus pending={feed.isPending} error={feed.isError ? feed.error : null} retrying={feed.isFetching} retry={() => void feed.refetch()} empty={feed.isSuccess && posts.length === 0} mine={source === 'mine'} name={name} words={words} />
      <div className="post-list">{posts.map((post) => <PostCard key={post.id} post={post} name={name} actions={actions} />)}</div>
      {feed.hasNextPage && <button type="button" className="button load-more" disabled={feed.isFetchingNextPage} onClick={() => void feed.fetchNextPage()}>Show older {words.posts}</button>}
    </section>
  )
}

function SourcePicker({ source, name, onChange }: { source: FeedSource; name: string; onChange: (source: FeedSource) => void }) {
  const choices: [FeedSource, string][] = [['all', 'Everyone'], ['companion', name], ['circle', 'Friends'], ['mine', 'You']]
  return (
    <div className="vibe-picks" role="group" aria-label="Whose posts">
      {choices.map(([id, label]) => <button key={id} type="button" className="vibe-pick" aria-pressed={source === id} onClick={() => onChange(id)}>{label}</button>)}
    </div>
  )
}

/** A post of the user's own. Every companion and their friends see it, and like or comment on it in their own time.
 * At rest it is a one-line field, so the first post stays in view on a phone; it opens up on focus or with text. */
function OwnPost({ onPosted, onError }: { onPosted: () => void; onError: (message: string) => void }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [focused, setFocused] = useState(false)
  const open = focused || text.length > 0
  const share = async () => {
    if (busy || !text.trim()) return
    setBusy(true)
    try {
      await api<FeedPost>('/feed/mine', { text: text.trim() })
      setText('')
      setFocused(false)
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
      onPosted()
    } catch (failure) { onError(failure instanceof Error ? failure.message : 'The post was not shared.') }
    setBusy(false)
  }
  const submit = (event: FormEvent) => { event.preventDefault(); void share() }
  return (
    <form className={`own-post${open ? ' open' : ''}`} onSubmit={submit} onFocus={() => setFocused(true)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false) }}>
      <label htmlFor="own-post-text" className="visually-hidden">Share something</label>
      <textarea id="own-post-text" rows={open ? 3 : 1} maxLength={1000} value={text} placeholder="Share something with everyone"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void share() } }} />
      {open && <div className="own-post-foot">
        <p className="subtle">Your companions and their friends see it, and may like or comment.</p>
        <button type="submit" className="button primary" disabled={busy || !text.trim()}>Post</button>
      </div>}
    </form>
  )
}

const unreadText = (count: number) => count ? `. ${count} new` : ''

function FeedStatus({ pending, error, retrying, retry, empty, mine, name, words }: { pending: boolean; error: Error | null; retrying: boolean; retry: () => void; empty: boolean; mine: boolean; name: string; words: EraWords }) {
  if (error) {
    const again = <button type="button" className="text-button" disabled={retrying} onClick={retry}>{retrying ? 'Trying again…' : 'Try again'}</button>
    return <ErrorNotice error={error} action={again}>The posts could not load. </ErrorNotice>
  }
  if (pending) return <Loading label="Loading the feed" />
  if (empty && mine) return <p className="subtle">Nothing from you yet. Write something above and everyone will see it.</p>
  return empty ? <p className="subtle">No {words.posts} yet. When something happens in {name}'s life or their friends', it shows up here.</p> : null
}

/** Posts on screen are marked read as soon as they are seen, so the header keeps the count the
 * reader arrived with, the number Today's "new in Feed" button showed, unless more come in. */
function useArrivalCount(unread: number | undefined): number {
  const [arrived, setArrived] = useState<number | null>(null)
  if (arrived === null && unread !== undefined) setArrived(unread)
  return Math.max(arrived ?? 0, unread ?? 0)
}
