import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'

export function SettingsPage() {
  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Settings"
        title="Account preferences"
        description="Manage product preferences for your ReFrame workspace."
      />

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {[
          ['Notifications', 'Email updates for room generation, brief sharing, and saved versions.'],
          ['Privacy', 'Control project visibility and data sharing with professionals.'],
          ['Exports', 'Future support for image downloads, briefs, and home summaries.'],
        ].map(([title, body]) => (
          <SurfaceCard key={title}>
            <p className="text-lg font-semibold text-ink-900">{title}</p>
            <p className="mt-3 text-sm leading-7 text-ink-500">{body}</p>
          </SurfaceCard>
        ))}
      </div>
    </div>
  )
}
