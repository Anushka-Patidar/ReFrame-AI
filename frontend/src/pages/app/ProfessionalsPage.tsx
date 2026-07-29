import { useEffect, useState } from 'react'
import { EditorialImage } from '../../components/EditorialImage'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { Professional } from '../../types/api'

export function ProfessionalsPage() {
  const [filters, setFilters] = useState({
    profession: 'Interior Designer',
    city: 'Indore',
  })
  const [professionals, setProfessionals] = useState<Professional[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    void api
      .listProfessionals(filters)
      .then(setProfessionals)
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load professionals.',
        ),
      )
  }, [filters])

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Professionals"
        title="Discover the people who can bring the brief into the real world."
        description="A curated practical directory for designers, craftspeople, and specialists who can execute the direction you have defined."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <SurfaceCard className="space-y-5">
        <div className="grid gap-4 md:grid-cols-3">
          <select
            value={filters.profession}
            onChange={(event) =>
              setFilters((current) => ({ ...current, profession: event.target.value }))
            }
            className="rounded-2xl border border-sand-200 bg-surface px-4 py-3 text-sm text-ink-700 outline-none"
          >
            <option>Interior Designer</option>
            <option>Carpenter</option>
            <option>Architect</option>
          </select>
          <input
            value={filters.city}
            onChange={(event) =>
              setFilters((current) => ({ ...current, city: event.target.value }))
            }
            className="rounded-2xl border border-sand-200 bg-surface px-4 py-3 text-sm text-ink-700 outline-none"
          />
          <div className="rounded-2xl border border-sand-200 bg-surface px-4 py-3 text-sm text-ink-700">
            Results: {professionals.length}
          </div>
        </div>
        <div className="grid gap-4">
          {professionals.map((professional) => (
            <div
              key={professional.id}
              className="grid gap-4 overflow-hidden rounded-[1.8rem] border border-sand-200 bg-sand-25 p-3 lg:grid-cols-[180px_1fr_auto]"
            >
              <EditorialImage
                src={professional.profession === 'Carpenter' ? editorialImages.study : editorialImages.living}
                alt={professional.name}
                className="min-h-[180px] rounded-[1.3rem]"
              />
              <div className="self-center">
                <p className="text-lg font-semibold text-ink-900">{professional.name}</p>
                <p className="mt-1 text-sm text-ink-500">{professional.profession}</p>
                <p className="mt-3 text-sm text-ink-500">
                  {professional.area} · {professional.experience_years} years · {professional.rating}★
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  className="rounded-2xl bg-ink-900 px-4 py-3 text-sm font-medium text-white"
                >
                  Contact
                </button>
                <button
                  type="button"
                  className="rounded-2xl border border-sand-200 bg-white px-4 py-3 text-sm font-medium text-ink-700"
                >
                  Share Brief
                </button>
              </div>
            </div>
          ))}
          {professionals.length === 0 ? (
            <div className="rounded-[24px] bg-sand-50 p-5 text-sm text-ink-500">
              No professionals match the current filters.
            </div>
          ) : null}
        </div>
      </SurfaceCard>
    </div>
  )
}
