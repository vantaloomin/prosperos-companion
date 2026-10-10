import { useEffect, useRef, useState, type FormEvent } from 'react'
import { EyeOff, Eye, MessageCircle, Trash2 } from 'lucide-react'
import type { FeedPost, Reaction } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { REACTIONS } from './feedState'
import { PostImage } from './PostImage'
import { Audience, SocialBody } from './SocialPost'
import { usePortrait } from '../conversation/portrait'
import { Stamp } from '../../components/Stamp'

export interface PostActions {
  react: (post: FeedPost, reaction: Reaction) => void
  hide: (post: FeedPost, hidden: boolean) => void
  remove: (post: FeedPost) => void
  discuss: (post: FeedPost, text: string) => Promise<boolean>
  answer: (post: FeedPost, option: string) => Promise<boolean>
  saw: (post: FeedPost) => void
  refresh: () => void
}

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
      <PostHeader post={post} name={name} />
      {post.intro && <p className="post-intro">{post.intro}</p>}
      <PostBody post={post} actions={actions} />
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

function PostBody({ post, actions }: { post: FeedPost; actions: PostActions }) {
  const imageFirst = post.events.length > 1
  return <>
    <PostEvents post={post} imageFirst={imageFirst} refresh={actions.refresh} />
    {post.source === 'social' && <SocialBody post={post} answer={actions.answer} />}
    {post.image && !imageFirst && <PostImage post={post} image={post.image} onChange={actions.refresh} />}
  </>
}

/** What happened. A post of several moments is illustrated by its first, so the picture sits under that one. */
function PostEvents({ post, imageFirst, refresh }: { post: FeedPost; imageFirst: boolean; refresh: () => void }) {
  return post.events.map((event, index) => (
    <div key={event.id} className="post-event">
      <p className="post-caption">{event.caption}</p>
      {event.caption !== event.summary && <p className="subtle">{event.summary}</p>}
      {index === 0 && imageFirst && post.image && <PostImage post={post} image={post.image} onChange={refresh} />}
    </div>
  ))
}

/** A friend's post says who they are to the companion ("Kimberly's mom"), never to the user. */
function PostHeader({ post, name }: { post: FeedPost; name: string }) {
  const role = post.author.role && `${name.trim().split(/\s+/)[0]}'s ${post.author.role}`
  return (
    <header className="post-header">
      <PostAvatar post={post} />
      <span id={`post-${post.id}`} className="speaker">{post.author.name}{role && <span className="post-role"> · {role}</span>}{!post.read && <span className="unread-dot" role="img" aria-label="unread" />}</span>
      <Stamp value={post.occurs_at} />
    </header>
  )
}

/** The poster's picture: the companion's profile picture on their own posts, everyone else's initial. */
function PostAvatar({ post }: { post: FeedPost }) {
  const portrait = usePortrait()
  if (post.author.kind === 'companion' && portrait) return <img className="post-avatar" src={portrait} alt="" aria-hidden="true" />
  return <span className="post-avatar" aria-hidden="true">{post.author.name.slice(0, 1).toUpperCase()}</span>
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
