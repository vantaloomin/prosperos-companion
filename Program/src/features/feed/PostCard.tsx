import { useEffect, useRef, useState, type FormEvent } from 'react'
import { EyeOff, Eye, MessageCircle, Send, Trash2, UserRound } from 'lucide-react'
import type { FeedPost, Reaction } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { REACTIONS } from './feedState'
import { PostImage } from './PostImage'
import { Audience, SocialBody } from './SocialPost'
import { usePortrait } from '../conversation/portrait'
import { Stamp } from '../../components/Stamp'
import { useEraWords } from '../world/useEraWords'
import { say } from '../world/eraWords'

export interface PostActions {
  react: (post: FeedPost, reaction: Reaction) => void
  hide: (post: FeedPost, hidden: boolean) => void
  remove: (post: FeedPost) => void
  discuss: (post: FeedPost, text: string) => Promise<boolean>
  comment: (post: FeedPost, text: string) => Promise<boolean>
  openChat: () => void
  answer: (post: FeedPost, option: string) => Promise<boolean>
  saw: (post: FeedPost) => void
  refresh: () => void
}

export function PostCard({ post, name, actions }: { post: FeedPost; name: string; actions: PostActions }) {
  const card = useRef<HTMLElement>(null)
  const [commenting, setCommenting] = useState(false)
  // The draft outlives closing the box, so closing it by mistake loses nothing.
  const [draft, setDraft] = useState('')
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
  // The user's own post: nothing to react to or talk over, only to take down.
  const own = post.source === 'user'
  return (
    <article ref={card} className={`post${hidden ? ' hidden-post' : ''}`} aria-labelledby={`post-${post.id}`}>
      <PostHeader post={post} name={name} />
      {post.intro && <p className="post-intro">{post.intro}</p>}
      <PostBody post={post} actions={actions} />
      <Audience audience={post.audience} thread={post.thread} poster={post.author.name} />
      <div className="post-actions">
        {!own && <>
          <span className="reactions" role="group" aria-label="React">
            {REACTIONS.map((reaction) => (
              <button key={reaction.id} type="button" className="reaction" aria-pressed={post.reaction === reaction.id} aria-label={reaction.label} onClick={() => actions.react(post, reaction.id)}>
                <span aria-hidden="true">{reaction.emoji}</span>
              </button>
            ))}
          </span>
          <button type="button" className="text-button" aria-expanded={commenting} onClick={() => setCommenting(!commenting)}><MessageCircle aria-hidden="true" />Comment</button>
          <button type="button" className="text-button" onClick={() => actions.hide(post, !hidden)}>{hidden ? <Eye aria-hidden="true" /> : <EyeOff aria-hidden="true" />}{hidden ? 'Show' : 'Hide'}</button>
        </>}
        <button type="button" className="text-button danger-text" onClick={() => setRemoving(true)}><Trash2 aria-hidden="true" />Remove</button>
      </div>
      {commenting && <CommentForm post={post} name={name} actions={actions} text={draft} setText={setDraft} onDone={() => setCommenting(false)} />}
      {removing && (
        <ConfirmDialog title="Remove this post?" onClose={() => setRemoving(false)} actions={<>
          <button type="button" className="button" onClick={() => setRemoving(false)}>Cancel</button>
          <button type="button" className="button danger" onClick={() => { setRemoving(false); actions.remove(post) }}>Remove</button>
        </>}>
          <p>{removeText(post, name)}</p>
        </ConfirmDialog>
      )}
    </article>
  )
}

function removeText(post: FeedPost, name: string) {
  if (post.source === 'user') return 'The post is removed for good, for everyone, with its likes and comments.'
  const life = post.source === 'life' ? ` What happened stays part of ${name}'s life and can still come up in conversation.` : ''
  return `The post is removed for good.${life} To keep it but out of sight, choose Hide instead.`
}

function PostBody({ post, actions }: { post: FeedPost; actions: PostActions }) {
  const imageFirst = post.events.length > 1
  return <>
    <PostEvents post={post} imageFirst={imageFirst} refresh={actions.refresh} />
    {post.source !== 'life' && <SocialBody post={post} answer={actions.answer} />}
    {post.image && !imageFirst && <PostImage post={post} image={post.image} onChange={actions.refresh} />}
  </>
}

/** What happened. A post of several moments is illustrated by its first, so the picture sits under that one. */
function PostEvents({ post, imageFirst, refresh }: { post: FeedPost; imageFirst: boolean; refresh: () => void }) {
  return post.events.map((event, index) => {
    // The post is the companion's own, so its lines say "I".
    const { caption, summary } = event.mine ?? event
    return <div key={event.id} className="post-event">
      <p className="post-caption">{caption}</p>
      {caption !== summary && <p className="subtle">{summary}</p>}
      {index === 0 && imageFirst && post.image && <PostImage post={post} image={post.image} onChange={refresh} />}
    </div>
  })
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

/** The poster's picture: the companion's profile picture on their own posts, a person on the user's, everyone else's initial. */
function PostAvatar({ post }: { post: FeedPost }) {
  const portrait = usePortrait()
  if (post.author.kind === 'companion' && portrait) return <img className="post-avatar" src={portrait} alt="" aria-hidden="true" />
  if (post.author.kind === 'user') return <span className="post-avatar" aria-hidden="true"><UserRound /></span>
  return <span className="post-avatar" aria-hidden="true">{post.author.name.slice(0, 1).toUpperCase()}</span>
}

/** A comment under the post, which whoever posted answers in the thread; or the same words sent to the companion in
 * chat, as a reply to the post. Commenting comes first: it is what the box looks like it does. */
function CommentForm({ post, name, actions, text, setText, onDone }: { post: FeedPost; name: string; actions: PostActions; text: string; setText: (text: string) => void; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const words = useEraWords()
  const first = name.trim().split(/\s+/)[0] || name
  const send = async (how: 'comment' | 'discuss') => {
    if (busy) return
    if (!text.trim()) {
      // Nothing typed: "Message … instead" just opens the chat.
      if (how === 'discuss') actions.openChat()
      return
    }
    setBusy(true)
    if (await actions[how](post, text.trim())) {
      setText('')
      onDone()
    }
    setBusy(false)
  }
  const submit = (event: FormEvent) => { event.preventDefault(); void send('comment') }
  return (
    <form className="discuss-form" onSubmit={submit}>
      <label className="visually-hidden" htmlFor={`comment-${post.id}`}>Write a comment</label>
      <textarea id={`comment-${post.id}`} rows={2} value={text} maxLength={1000} autoFocus placeholder="Write a comment"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void send('comment') }
          if (event.key === 'Escape') { event.preventDefault(); onDone() }
        }} />
      <div className="form-actions discuss-actions">
        <button type="submit" className="button primary" disabled={busy || !text.trim()}>Comment</button>
        <button type="button" className="text-button" disabled={busy} onClick={() => void send('discuss')}><Send aria-hidden="true" />{say(words, 'message_to', first)} instead</button>
      </div>
    </form>
  )
}
