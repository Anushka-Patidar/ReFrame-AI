import type { ReactNode } from 'react'

type SurfaceCardProps = {
  children: ReactNode
  className?: string
}

export function SurfaceCard({ children, className = '' }: SurfaceCardProps) {
  return (
    <div
      className={`rounded-[2rem] border border-sand-200/80 bg-[linear-gradient(180deg,rgba(255,252,248,0.94),rgba(250,246,240,0.9))] p-6 shadow-[var(--shadow-soft)] backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-[var(--shadow-float)] ${className}`}
    >
      {children}
    </div>
  )
}

type MetricCardProps = {
  label: string
  value: string
  helper?: string
}

export function MetricCard({ label, value, helper }: MetricCardProps) {
  return (
    <SurfaceCard className="space-y-4">
      <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
        {label}
      </p>
      <p className="font-editorial text-4xl tracking-tight text-ink-950">{value}</p>
      {helper ? <p className="text-sm leading-6 text-ink-500">{helper}</p> : null}
    </SurfaceCard>
  )
}
