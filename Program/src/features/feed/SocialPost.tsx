import { useState } from 'react'
import { MapPin } from 'lucide-react'
import type { FeedPost } from '../../types'

const LABELS: Partial<Record<FeedPost['kind'], string>> = {
  birthday: 'Birthday', holiday: 'Holiday', city: 'Around town', question: 'Asking you',
}

/** The text of a post that is not a life event: a friend's update, a passing thought, a shout-out, city news or a question. */
export function SocialBody({ post, answer }: { post: FeedPost; answer: (post: FeedPost, option: string) => Promise<boolean> }) {
  const label = LABELS[post.kind]
  return (
    <div className="post-event">
      {label && <p className="post-label">{label}</p>}
      <p className="post-caption">{post.text}</p>
      {post.context && post.context !== post.text && <p className="subtle">{post.context}</p>}
      {post.place && <p className="post-place subtle"><MapPin aria-hidden="true" />{post.place}</p>}
      {post.kind === 'question' && <Choices post={post} answer={answer} />}
    </div>
  )
}

function Choices({ post, answer }: { post: FeedPost; answer: (post: FeedPost, option: string) => Promise<boolean> }) {
  const [busy, setBusy] = useState(false)
  const pick = async (option: string) => {
    setBusy(true)
    await answer(post, option)
    setBusy(false)
  }
  return (
    <div className="vibe-picks" role="group" aria-label="Your answer">
      {(post.options ?? []).map((option) => (
        <button key={option} type="button" className="vibe-pick" aria-pressed={post.answer === option} disabled={busy} onClick={() => void pick(option)}>{option}</button>
      ))}
    </div>
  )
}

const names = (likes: string[]) => likes.length <= 2 ? likes.join(' and ') : `${likes.slice(0, 2).join(', ')} and ${likes.length - 2} more`

/** Likes and comments from the companion's circle (and from the companion, on friends' posts). */
export function Audience({ audience }: { audience: FeedPost['audience'] }) {
  if (!audience.likes.length && !audience.comments.length) return null
  return (
    <div className="post-audience">
      {audience.likes.length > 0 && <p className="subtle"><span aria-hidden="true">❤️ </span>Liked by {names(audience.likes)}</p>}
      {audience.comments.length > 0 && (
        <ul className="post-comments" aria-label="Comments">
          {audience.comments.map((comment) => <li key={`${comment.name}-${comment.at}`}><strong>{comment.name}</strong> {comment.text}</li>)}
        </ul>
      )}
    </div>
  )
}
