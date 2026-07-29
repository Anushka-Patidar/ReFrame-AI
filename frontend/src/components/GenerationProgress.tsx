import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const FALLBACK_STAGES = [
  'Analyzing your room',
  'Preparing your design',
  'Redesigning the interior',
  'Refining your room',
] as const

type Props = {
  active: boolean
}

export function GenerationProgress({ active }: Props) {
  const [label, setLabel] = useState<string>(FALLBACK_STAGES[0])

  useEffect(() => {
    if (!active) {
      setLabel(FALLBACK_STAGES[0])
      return
    }

    let cancelled = false
    let fallbackIndex = 0
    let receivedLive = false

    const poll = async () => {
      try {
        const status = await api.getGenerationStatus()
        if (cancelled) return
        if (status.busy && status.label) {
          receivedLive = true
          setLabel(status.label)
        }
      } catch {
        // Fall back to timed stage labels below.
      }
    }

    void poll()
    const pollId = window.setInterval(() => {
      void poll()
    }, 1200)

    const fallbackId = window.setInterval(() => {
      if (cancelled || receivedLive) return
      fallbackIndex = (fallbackIndex + 1) % FALLBACK_STAGES.length
      setLabel(FALLBACK_STAGES[fallbackIndex])
    }, 9000)

    return () => {
      cancelled = true
      window.clearInterval(pollId)
      window.clearInterval(fallbackId)
    }
  }, [active])

  if (!active) return null

  return (
    <div className="rounded-[1.5rem] border border-sand-200 bg-sand-25 px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-500/40" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent-600" />
        </span>
        <p className="text-sm font-medium text-ink-900">{label}</p>
      </div>
      <p className="mt-2 text-sm leading-6 text-ink-500">
        This can take a few minutes on this device. ReFrame will not show a fake result.
      </p>
    </div>
  )
}
