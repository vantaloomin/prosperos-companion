import { useState } from 'react'
import type { StoryChapter } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { ExportLinks } from '../chats/ExportLinks'
import { chapterWhen, lineTime } from './storyText'

/** The Story is one ongoing story, in chapters (companion/story_chapters.py). A chapter's number and when it began
 * stand above its first line. One waiting for its first line stands at the end and says nothing was lost; the
 * user's own can be taken back until something is said in it. */
export function ChapterHeading({ chapter, onUndo }: { chapter: StoryChapter; onUndo?: () => void }) {
  return (
    <div className="story-chapter">
      <h2>Chapter {chapter.number}</h2>
      <p>{chapterWhen(chapter.local_time)}</p>
      {chapter.by && <p>A new chapter of the same story. Everything before it still happened.
        {chapter.by === 'asked' && onUndo && <> <button type="button" className="text-button" onClick={onUndo}>Undo</button></>}</p>}
    </div>
  )
}

/** "8:06 PM" on a line: the hour it was there, on the city's clock as the scene's own time is. */
export function LineTime({ at, began }: { at: string; began?: string }) {
  return <time className="story-time" dateTime={at}>{lineTime(at, began)}</time>
}

interface FooterProps { empty: boolean; waiting: boolean; busy: boolean; onChapter: () => void; onClear: () => Promise<void> }

/** Under the box: keep a copy, start a new chapter (nothing is cleared), or clear the written pages. */
export function StoryFooter({ empty, waiting, busy, onChapter, onClear }: FooterProps) {
  const [asking, setAsking] = useState(false)
  if (empty) return null
  return (
    <div className="story-footer">
      <ExportLinks target={{ kind: 'story' }} />
      {!waiting && <button type="button" className="text-button" disabled={busy} onClick={onChapter}>Start a new chapter</button>}
      <button type="button" className="text-button" onClick={() => setAsking(true)}>Clear the pages…</button>
      {asking && <ConfirmDialog title="Clear the story's pages?" onClose={() => setAsking(false)} actions={<>
        <button type="button" className="button" onClick={() => setAsking(false)}>Cancel</button>
        <button type="button" className="button danger" onClick={() => void onClear().then(() => setAsking(false))}>Clear the pages</button>
      </>}>
        <p>Every chapter written so far is removed for good.</p>
        <p>Only the pages go. The people you&apos;ve met still know you, your time with companions still counts, and you stay where you are.</p>
        <p className="subtle">To keep a copy, export it first:</p>
        <p className="form-actions"><ExportLinks target={{ kind: 'story' }} /></p>
      </ConfirmDialog>}
    </div>
  )
}
