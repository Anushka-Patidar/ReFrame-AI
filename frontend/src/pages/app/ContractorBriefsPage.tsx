import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../lib/api'
import type { ContractorBrief } from '../../types/api'
import { getLatestRoomAndDesign } from '../../utils/project'

export function ContractorBriefsPage() {
  const { token } = useAuth()
  const [searchParams] = useSearchParams()
  const [briefs, setBriefs] = useState<ContractorBrief[]>([])
  const [error, setError] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  useEffect(() => {
    if (!token) return

    void api
      .listBriefs(token)
      .then(setBriefs)
      .catch((requestError) =>
        setError(
          requestError instanceof Error ? requestError.message : 'Unable to load briefs.',
        ),
      )
  }, [token])

  async function generateBrief() {
    if (!token) return

    setIsGenerating(true)
    setError('')
    try {
      const designId =
        searchParams.get('designId') ?? (await getLatestRoomAndDesign(token)).design?.id ?? null
      if (!designId) {
        throw new Error('No generated design found to create a brief.')
      }
      const brief = await api.generateBrief(token, designId)
      setBriefs((current) => [brief, ...current.filter((item) => item.id !== brief.id)])
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Unable to generate brief.',
      )
    } finally {
      setIsGenerating(false)
    }
  }

  const activeBrief = briefs[0] ?? null

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Contractor Briefs"
        title="Move from concept to execution"
        description="Approved room versions become concise briefs that a carpenter, designer, electrician, or contractor can act on."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <SurfaceCard className="space-y-4">
          <p className="text-lg font-semibold text-ink-900">
            {activeBrief?.room_name ?? 'No contractor brief yet'}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ['Room Size', activeBrief?.room_size ?? '-'],
              ['Design Style', activeBrief?.style ?? '-'],
              ['Budget', activeBrief ? `₹${activeBrief.budget.toLocaleString('en-IN')}` : '-'],
              ['Keep Existing', activeBrief?.keep_existing.join(', ') ?? '-'],
              ['Remove', activeBrief?.remove.join(', ') ?? '-'],
              ['Lighting', activeBrief?.lighting.join(', ') ?? '-'],
            ].map(([label, value]) => (
              <div key={label} className="rounded-[24px] bg-sand-50 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-ink-500">{label}</p>
                <p className="mt-3 text-sm leading-6 text-ink-900">{value}</p>
              </div>
            ))}
          </div>
        </SurfaceCard>
        <SurfaceCard className="space-y-4">
          <button
            type="button"
            onClick={generateBrief}
            disabled={isGenerating}
            className="inline-flex w-full justify-center rounded-2xl bg-ink-900 px-4 py-3 text-sm font-medium text-white"
          >
            {isGenerating ? 'Generating...' : 'Generate Contractor Brief'}
          </button>
          <button
            type="button"
            className="inline-flex w-full justify-center rounded-2xl border border-sand-200 bg-white px-4 py-3 text-sm font-medium text-ink-700"
          >
            Share Brief
          </button>
        </SurfaceCard>
      </div>
    </div>
  )
}
