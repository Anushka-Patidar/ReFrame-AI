import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MetricCard, SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../lib/api'
import type { DesignScore } from '../../types/api'
import { getLatestRoomAndDesign } from '../../utils/project'

export function DesignScorePage() {
  const { token } = useAuth()
  const [searchParams] = useSearchParams()
  const [score, setScore] = useState<DesignScore | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return

    const explicitDesignId = searchParams.get('designId')
    const load = async () => {
      try {
        const designId =
          explicitDesignId ?? (await getLatestRoomAndDesign(token)).design?.id ?? null
        if (!designId) return
        const nextScore = await api.getScore(token, designId)
        setScore(nextScore)
      } catch (requestError) {
        setError(
          requestError instanceof Error ? requestError.message : 'Unable to load score.',
        )
      }
    }

    void load()
  }, [searchParams, token])

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Design Score"
        title="Guidance backed by AI and spatial checks"
        description="The scoring layer blends qualitative design analysis with Python-based space and budget heuristics."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <MetricCard
          label="Overall Score"
          value={`${score?.total_score ?? 0}/100`}
          helper="For the latest generated version"
        />
        <SurfaceCard>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {Object.entries(score?.categories ?? {}).map(([label, value]) => (
              <div key={label} className="rounded-[24px] bg-sand-50 p-4">
                <p className="text-sm text-ink-500">{label.replaceAll('_', ' ')}</p>
                <p className="mt-4 text-2xl font-semibold text-ink-900">{value}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-[24px] bg-sand-50 p-5">
              <p className="font-medium text-ink-900">AI observation</p>
              <p className="mt-3 text-sm leading-7 text-ink-500">
                {score?.observation ?? 'Generate a design to see scoring guidance.'}
              </p>
            </div>
            <div className="rounded-[24px] bg-sand-50 p-5">
              <p className="font-medium text-ink-900">Potential improvement</p>
              <p className="mt-3 text-sm leading-7 text-ink-500">
                {score?.recommendation ?? 'Additional recommendations will appear here.'}
              </p>
            </div>
          </div>
        </SurfaceCard>
      </div>
    </div>
  )
}
