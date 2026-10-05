// Original tones made on the spot with Web Audio; no recorded sounds ship with the app.
type Cue = 'message'

const NOTES: Record<Cue, number[]> = {
  message: [880, 1174.66],
}

let context: AudioContext | null = null

export function playCue(cue: Cue) {
  try {
    context ??= new AudioContext()
    const start = context.currentTime
    NOTES[cue].forEach((frequency, index) => {
      const oscillator = context!.createOscillator()
      const gain = context!.createGain()
      const at = start + index * 0.09
      oscillator.type = 'triangle'
      oscillator.frequency.value = frequency
      gain.gain.setValueAtTime(0.0001, at)
      gain.gain.exponentialRampToValueAtTime(0.12, at + 0.015)
      gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.16)
      oscillator.connect(gain).connect(context!.destination)
      oscillator.start(at)
      oscillator.stop(at + 0.18)
    })
  } catch { /* No audio device or autoplay refused: the cue is a nicety, never needed. */ }
}

