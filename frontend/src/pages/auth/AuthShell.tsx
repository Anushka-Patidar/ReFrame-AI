import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

type AuthShellProps = {
  title: string
  subtitle: string
  footer: ReactNode
  children: ReactNode
}

export function AuthShell({ title, subtitle, footer, children }: AuthShellProps) {
  return (
    <div className="grid min-h-screen bg-surface lg:grid-cols-[1fr_440px]">
      <section className="hidden bg-[linear-gradient(160deg,#efe3d4,#fffdf9)] p-12 lg:flex lg:flex-col lg:justify-between">
        <Link to="/" className="flex items-center gap-4 text-ink-900">
          <img
            src="/reframe-logo.png"
            alt="ReFrame"
            className="h-14 w-14 rounded-[1rem] object-cover ring-1 ring-sand-200"
          />
          <div>
            <p className="font-editorial text-3xl tracking-[-0.04em]">ReFrame</p>
            <p className="text-[0.65rem] uppercase tracking-[0.26em] text-ink-500">
              Reimagine your space
            </p>
          </div>
        </Link>
        <div className="space-y-6">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-accent-600">
            AI Design Studio
          </p>
          <h1 className="font-editorial max-w-xl text-6xl leading-[0.92] tracking-[-0.05em] text-ink-900">
            Turn your real room into a design project with memory.
          </h1>
          <p className="max-w-xl text-lg leading-8 text-ink-500">
            ReFrame connects room photos, structured requirements, style continuity,
            design scoring, and contractor-ready execution briefs.
          </p>
        </div>
        <div className="rounded-[28px] border border-white/70 bg-white/70 p-6 shadow-soft">
          <p className="text-sm text-ink-500">What users get after login</p>
          <ul className="mt-4 space-y-3 text-sm text-ink-700">
            <li>Design a new room from a real upload</li>
            <li>Discuss changes and save V1, V2, V3, and more</li>
            <li>Track your home style across rooms</li>
          </ul>
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-md rounded-[2rem] border border-sand-200/70 bg-[linear-gradient(180deg,rgba(255,252,248,0.96),rgba(248,243,236,0.92))] p-8 shadow-[var(--shadow-soft)]">
          <div className="mb-8">
            <Link to="/" className="inline-flex items-center gap-3 text-lg font-semibold text-ink-900 lg:hidden">
              <img
                src="/reframe-logo.png"
                alt="ReFrame"
                className="h-11 w-11 rounded-[0.9rem] object-cover ring-1 ring-sand-200"
              />
              <span className="font-editorial text-3xl tracking-[-0.04em]">ReFrame</span>
            </Link>
            <h2 className="font-editorial mt-5 text-4xl leading-none tracking-[-0.04em] text-ink-900">
              {title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink-500">{subtitle}</p>
          </div>
          {children}
          <div className="mt-8 text-sm text-ink-500">{footer}</div>
        </div>
      </section>
    </div>
  )
}
