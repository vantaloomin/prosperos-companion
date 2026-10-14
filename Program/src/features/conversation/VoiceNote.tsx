import { useEffect, useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import type { VoiceNote as Note } from '../../types'
import { useWhere } from './useWhere'
import { onCall } from './whereText'
import { clockLength, playsByItself } from './voiceLength'

// Replies already played by themselves on a call, and the one playing now, so one voice speaks at a time.
const heard = new Set<string>()
let speaking: HTMLAudioElement | null = null

/** A voice note in place of a text bubble: play, how far along it is, its length, and the words underneath. On a call
 * (companion/life/calls.py) a reply that just arrived plays by itself, as a voice on the phone would. */
export function VoiceNote({ note, text, name, at: arrived = null }: { note: Note; text: string; name: string; at?: string | null }) {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [at, setAt] = useState(0)
  const [length, setLength] = useState(note.duration_ms ? note.duration_ms / 1000 : 0)
  const [failed, setFailed] = useState(false)
  const calling = onCall(useWhere().data)
  useEffect(() => () => audio.current?.pause(), [])
  useEffect(() => {
    const player = audio.current
    if (!player || !calling || heard.has(note.url) || !playsByItself(arrived, Date.now())) return
    heard.add(note.url)
    speaking?.pause()
    speaking = player
    void player.play().catch(() => undefined)  // A browser that blocks it leaves Play to the user.
  }, [calling, arrived, note.url])
  const toggle = () => {
    const player = audio.current
    if (!player) return
    if (player.paused) void player.play().catch(() => setFailed(true))
    else player.pause()
  }
  const progress = length ? Math.min(100, (at / length) * 100) : 0
  return (
    <div className="voice-note">
      <div className="voice-note-player">
        <button type="button" className="voice-note-play" onClick={toggle} aria-label={playing ? `Pause ${name}'s voice note` : `Play ${name}'s voice note`} disabled={failed}>
          {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
        </button>
        <span className="voice-note-track" aria-hidden="true"><span style={{ width: `${progress}%` }} /></span>
        <span className="voice-note-length">{clockLength(playing || at ? at : length)}</span>
        <audio ref={audio} src={note.url} preload="metadata"
          onLoadedMetadata={(event) => Number.isFinite(event.currentTarget.duration) && setLength(event.currentTarget.duration)}
          onTimeUpdate={(event) => setAt(event.currentTarget.currentTime)}
          onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
          onEnded={() => { setPlaying(false); setAt(0) }} onError={() => setFailed(true)} />
      </div>
      {failed && <p className="subtle voice-note-missing">This voice note cannot be played.</p>}
      <p className="voice-note-words">{text}</p>
    </div>
  )
}
