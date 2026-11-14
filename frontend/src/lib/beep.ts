/**
 * Audible alert for HIGH alarms (REQ-005) with the Web Audio API.
 *
 * Simplified demo pattern: three 880 Hz pulses every 2.5 s while a HIGH alarm is ACTIVE.
 * This is NOT the IEC 60601-1-8 high-priority melody; the real sound design is a Sprint 4
 * usability item. Browsers only allow audio after a user gesture, so `unlock()` is called
 * from the Sign-in click.
 */
export interface AlarmSound {
  unlock(): void
  start(): void
  stop(): void
  readonly playing: boolean
}

type AudioContextCtor = new () => AudioContext

function audioContextCtor(): AudioContextCtor | undefined {
  if (typeof window === 'undefined') return undefined
  const w = window as unknown as { AudioContext?: AudioContextCtor; webkitAudioContext?: AudioContextCtor }
  return w.AudioContext ?? w.webkitAudioContext
}

const PULSES = 3
const PULSE_S = 0.15
const GAP_S = 0.1
const REPEAT_MS = 2500

export function createAlarmSound(): AlarmSound {
  let ctx: AudioContext | undefined
  let timer: ReturnType<typeof setInterval> | undefined

  const context = (): AudioContext | undefined => {
    if (!ctx) {
      const Ctor = audioContextCtor()
      if (!Ctor) return undefined // e.g. jsdom in unit tests
      ctx = new Ctor()
    }
    if (ctx.state === 'suspended') void ctx.resume()
    return ctx
  }

  const burst = () => {
    const c = context()
    if (!c) return
    for (let i = 0; i < PULSES; i++) {
      const at = c.currentTime + i * (PULSE_S + GAP_S)
      const osc = c.createOscillator()
      const gain = c.createGain()
      osc.type = 'square'
      osc.frequency.value = 880
      gain.gain.setValueAtTime(0.0001, at)
      gain.gain.exponentialRampToValueAtTime(0.2, at + 0.01)
      gain.gain.exponentialRampToValueAtTime(0.0001, at + PULSE_S)
      osc.connect(gain).connect(c.destination)
      osc.start(at)
      osc.stop(at + PULSE_S + 0.02)
    }
  }

  return {
    unlock() {
      context()
    },
    start() {
      if (timer !== undefined) return
      burst()
      timer = setInterval(burst, REPEAT_MS)
    },
    stop() {
      if (timer !== undefined) clearInterval(timer)
      timer = undefined
    },
    get playing() {
      return timer !== undefined
    },
  }
}
