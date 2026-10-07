import { useEffect, useMemo, useState } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, newId } from '../../api'
import { HISTORY_KEY, type View } from '../../companion'
import type { Companion, FeedPage, FeedPost, FeedSource } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { PostCard, type PostActions } from './PostCard'
import { ReadBatcher, joinPages, nextReaction } from './feedState'
import { isActive } from './imageState'

export function Feed({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const [hidden, setHidden] = useState(false)
  const [source, setSource] = useState<FeedSource>('all')
  const [error, setError] = useState<string | null>(null)
  const key = useMemo(() => ['feed', hidden, source], [hidden, source])
  const feed = useInfiniteQuery({
    queryKey: key,
    queryFn: ({ pageParam }) => api<FeedPage>(`/feed?limit=20&hidden=${hidden}&source=${source}${pageParam ? `&before=${encodeURIComponent(pageParam)}` : ''}`),
    initialPageParam: '',
    getNextPageParam: (last) => last.next_before ?? undefined,
    // While an image is being made, look again every few seconds.
    refetchInterval: (query) => query.state.data?.pages.some((page) => page.posts.some((post) => post.image && isActive(post.image.status))) ? 3000 : false,
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
          <h1>Feed</h1>
          <p className="subtle">{name}'s posts, and what their friends are up to{unreadText(unread)}. Only you see them.</p>
        </div>
        <button type="button" className="button" onClick={() => void exportFeed()}><Download aria-hidden="true" />Export</button>
      </header>
      <div className="memory-toolbar">
        <SourcePicker source={source} name={name} onChange={setSource} />
        <Toggle label="Show hidden posts" checked={hidden} onChange={setHidden} />
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      <FeedStatus pending={feed.isPending} error={feed.error} empty={feed.isSuccess && posts.length === 0} name={name} />
      <div className="post-list">{posts.map((post) => <PostCard key={post.id} post={post} name={name} actions={actions} />)}</div>
      {feed.hasNextPage && <button type="button" className="button load-more" disabled={feed.isFetchingNextPage} onClick={() => void feed.fetchNextPage()}>Show older posts</button>}
    </section>
  )
}

function SourcePicker({ source, name, onChange }: { source: FeedSource; name: string; onChange: (source: FeedSource) => void }) {
  const choices: [FeedSource, string][] = [['all', 'Everyone'], ['companion', name], ['circle', 'Friends']]
  return (
    <div className="vibe-picks" role="group" aria-label="Whose posts">
      {choices.map(([id, label]) => <button key={id} type="button" className="vibe-pick" aria-pressed={source === id} onClick={() => onChange(id)}>{label}</button>)}
    </div>
  )
}

const unreadText = (count: number) => count ? `. ${count} new` : ''

function FeedStatus({ pending, error, empty, name }: { pending: boolean; error: Error | null; empty: boolean; name: string }) {
  if (pending) return <Loading label="Loading the feed" />
  if (error) return <Notice tone="error">{error.message}</Notice>
  return empty ? <p className="subtle">No posts yet. When something happens in {name}'s life or their friends', it shows up here.</p> : null
}

/** Posts on screen are marked read as soon as they are seen, so the header keeps the count the
 * reader arrived with, the number Today's "new in Feed" button showed, unless more come in. */
function useArrivalCount(unread: number | undefined): number {
  const [arrived, setArrived] = useState<number | null>(null)
  if (arrived === null && unread !== undefined) setArrived(unread)
  return Math.max(arrived ?? 0, unread ?? 0)
}
