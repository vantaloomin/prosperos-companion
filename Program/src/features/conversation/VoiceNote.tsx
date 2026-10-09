import { useEffect, useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import type { VoiceNote as Note } from '../../types'
import { clockLength } from './voiceLength'

/** A voice note in place of a text bubble: play, how far along it is, its length, and the words underneath. */
export function VoiceNote({ note, text, name }: { note: Note; text: string; name: string }) {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [at, setAt] = useState(0)
  const [length, setLength] = useState(note.duration_ms ? note.duration_ms / 1000 : 0)
  const [failed, setFailed] = useState(false)
  useEffect(() => () => audio.current?.pause(), [])
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
