type SectionHeaderProps = {
  eyebrow?: string
  title: string
  description?: string
  align?: 'start' | 'center'
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  align = 'start',
}: SectionHeaderProps) {
  return (
    <div className={`space-y-3 ${align === 'center' ? 'text-center' : ''}`}>
      {eyebrow ? (
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.34em] text-accent-600">
          {eyebrow}
        </p>
      ) : null}
      <div className="space-y-2">
        <h2 className="font-editorial text-4xl leading-none tracking-[-0.03em] text-ink-950 sm:text-5xl">
          {title}
        </h2>
        {description ? (
          <p
            className={`text-sm leading-7 text-ink-500 sm:text-base ${align === 'center' ? 'mx-auto max-w-2xl' : 'max-w-2xl'}`}
          >
            {description}
          </p>
        ) : null}
      </div>
    </div>
  )
}
