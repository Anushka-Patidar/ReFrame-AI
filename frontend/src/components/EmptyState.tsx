import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EditorialImage } from './EditorialImage'

type EmptyStateProps = {
  title: string
  description: string
  actionLabel: string
  actionHref: string
  imageSrc?: string
}

export function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
  imageSrc,
}: EmptyStateProps) {
  return (
    <div className="grid gap-5 rounded-[2rem] border border-sand-200/80 bg-[linear-gradient(180deg,rgba(255,252,248,0.95),rgba(246,240,232,0.92))] p-5 lg:grid-cols-[240px_1fr]">
      <EditorialImage
        src={imageSrc}
        alt={title}
        className="min-h-48 rounded-[1.5rem]"
      />
      <div className="flex flex-col justify-between gap-4">
        <div className="space-y-3">
          <p className="text-2xl font-medium tracking-tight text-ink-900">{title}</p>
          <p className="max-w-xl text-sm leading-7 text-ink-500">{description}</p>
        </div>
        <Link
          to={actionHref}
          className="inline-flex w-fit items-center gap-2 rounded-full bg-ink-900 px-5 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5"
        >
          {actionLabel}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}
