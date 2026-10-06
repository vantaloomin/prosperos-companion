import { useEffect, useRef, useState, type FormEvent } from 'react'
import { EyeOff, Eye, MessageCircle, Trash2 } from 'lucide-react'
import type { FeedPost, Reaction } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { REACTIONS } from './feedState'
import { PostImage } from './PostImage'
import { Audience, SocialBody } from './SocialPost'

export interface PostActions {
  react: (post: FeedPost, reaction: Reaction) => void
  hide: (post: FeedPost, hidden: boolean) => void
  remove: (post: FeedPost) => void
  discuss: (post: FeedPost, text: string) => Promise<boolean>
  answer: (post: FeedPost, option: string) => Promise<boolean>
  saw: (post: FeedPost) => void
  refresh: () => void
}

const when = (value: string) => new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }).format(new Date(value))

export function PostCard({ post, name, actions }: { post: FeedPost; name: string; actions: PostActions }) {
  const card = useRef<HTMLElement>(null)
  const [discussing, setDiscussing] = useState(false)
  const [removing, setRemoving] = useState(false)
  // Counted as read only once at least half of the post has been on screen.
  const saw = useRef(() => actions.saw(post))
  useEffect(() => { saw.current = () => actions.saw(post) })
  useEffect(() => {
    const element = card.current
    if (post.read || !element || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { saw.current(); observer.disconnect() } }, { threshold: 0.5 })
    observer.observe(element)
    return () => observer.disconnect()
  }, [post.read])
  const hidden = post.status === 'hidden'
  return (
    <article ref={card} className={`post${hidden ? ' hidden-post' : ''}`} aria-labelledby={`post-${post.id}`}>
      <PostHeader post={post} />
      {post.intro && <p className="post-intro">{post.intro}</p>}
      {post.events.map((event) => (
        <div key={event.id} className="post-event">
          <p className="post-caption">{event.caption}</p>
          {event.caption !== event.summary && <p className="subtle">{event.summary}</p>}
        </div>
      ))}
      {post.source === 'social' && <SocialBody post={post} answer={actions.answer} />}
      {post.image && <PostImage post={post} image={post.image} onChange={actions.refresh} />}
      <Audience audience={post.audience} />
      <div className="post-actions">
        <span className="reactions" role="group" aria-label="React">
          {REACTIONS.map((reaction) => (
            <button key={reaction.id} type="button" className="reaction" aria-pressed={post.reaction === reaction.id} aria-label={reaction.label} onClick={() => actions.react(post, reaction.id)}>
              <span aria-hidden="true">{reaction.emoji}</span>
            </button>
          ))}
        </span>
        <button type="button" className="text-button" aria-expanded={discussing} onClick={() => setDiscussing(!discussing)}><MessageCircle aria-hidden="true" />Talk about this</button>
        <button type="button" className="text-button" onClick={() => actions.hide(post, !hidden)}>{hidden ? <Eye aria-hidden="true" /> : <EyeOff aria-hidden="true" />}{hidden ? 'Show' : 'Hide'}</button>
        <button type="button" className="text-button danger-text" onClick={() => setRemoving(true)}><Trash2 aria-hidden="true" />Remove</button>
      </div>
      {discussing && <DiscussForm post={post} name={name} discuss={actions.discuss} onDone={() => setDiscussing(false)} />}
      {removing && (
        <ConfirmDialog title="Remove this post?" onClose={() => setRemoving(false)} actions={<>
          <button type="button" className="button" onClick={() => setRemoving(false)}>Cancel</button>
          <button type="button" className="button danger" onClick={() => { setRemoving(false); actions.remove(post) }}>Remove</button>
        </>}>
          <p>{post.source === 'life' ? `The post is removed for good. What happened stays part of ${name}'s life and can still come up in conversation.` : 'The post is removed for good.'} To keep it but out of sight, choose Hide instead.</p>
        </ConfirmDialog>
      )}
    </article>
  )
}

function PostHeader({ post }: { post: FeedPost }) {
  return (
    <header className="post-header">
      <span id={`post-${post.id}`} className="speaker">{post.author.name}{post.author.role && <span className="post-role"> · {post.author.role}</span>}{!post.read && <span className="unread-dot" aria-label="unread" />}</span>
      <time dateTime={post.occurs_at}>{when(post.occurs_at)}</time>
    </header>
  )
}

function DiscussForm({ post, name, discuss, onDone }: { post: FeedPost; name: string; discuss: PostActions['discuss']; onDone: () => void }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    if (await discuss(post, text.trim())) onDone()
    setBusy(false)
  }
  return (
    <form className="discuss-form" onSubmit={submit}>
      <label className="visually-hidden" htmlFor={`discuss-${post.id}`}>Message {name} about this post</label>
      <textarea id={`discuss-${post.id}`} rows={2} value={text} maxLength={40000} autoFocus placeholder={`Message ${name} about this`} onChange={(event) => setText(event.target.value)} />
      <div className="form-actions"><button type="submit" className="button primary" disabled={busy || !text.trim()}>Send in Chat</button></div>
    </form>
  )
}
