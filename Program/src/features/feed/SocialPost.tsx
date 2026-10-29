import { useState } from 'react'
import { MapPin } from 'lucide-react'
import type { FeedPost, ThreadComment } from '../../types'

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

/** Likes and comments from the companion's circle (and from the companion, on friends' posts). On the user's own
 * posts, every companion and their circles, each friend of a friend with whose they are. Then the user's own comments,
 * each with the answer it got from whoever posted. */
export function Audience({ audience, thread, poster }: { audience: FeedPost['audience']; thread?: FeedPost['thread']; poster: string }) {
  const own = thread?.comments ?? []
  if (!audience.likes.length && !audience.comments.length && !own.length) return null
  return (
    <div className="post-audience">
      {audience.likes.length > 0 && <p className="subtle"><span aria-hidden="true">❤️ </span>Liked by {names(audience.likes)}</p>}
      <Comments comments={audience.comments} own={own} />
      {thread?.waiting && <p className="subtle post-waiting">{firstName(poster)} hasn't seen your comment yet.</p>}
    </div>
  )
}

function Comments({ comments, own }: { comments: FeedPost['audience']['comments']; own: ThreadComment[] }) {
  if (!comments.length && !own.length) return null
  return (
    <ul className="post-comments" aria-label="Comments">
      {comments.map((comment) => <li key={`${comment.name}-${comment.at}`}><strong>{comment.name}</strong>{comment.role && <span className="post-role"> · {comment.role}</span>} {comment.text}</li>)}
      {own.map((comment) => <ThreadLine key={comment.id} comment={comment} />)}
    </ul>
  )
}

const firstName = (name: string) => name.trim().split(/\s+/)[0] || name

function ThreadLine({ comment }: { comment: ThreadComment }) {
  if (comment.author === 'user') return <li className="post-comment-yours"><strong>You</strong> {comment.text}</li>
  return <li className="post-comment-answer"><strong>{comment.name}</strong> {comment.text}</li>
}
