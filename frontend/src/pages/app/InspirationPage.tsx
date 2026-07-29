import { useEffect, useMemo, useState } from 'react'
import { EditorialImage } from '../../components/EditorialImage'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { Inspiration } from '../../types/api'

export function InspirationPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<Inspiration[]>([])
  const [imageUrl, setImageUrl] = useState('')
  const [tagInput, setTagInput] = useState('Warm lighting, Neutral colours')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!token) return
    void api
      .listInspirations(token)
      .then(setItems)
      .catch((requestError) =>
        setError(
          requestError instanceof Error ? requestError.message : 'Unable to load inspirations.',
        ),
      )
  }, [token])

  const tags = useMemo(
    () =>
      [...new Set(items.flatMap((item) => item.detected_tags))]
        .filter(Boolean)
        .sort((left, right) => left.localeCompare(right)),
    [items],
  )

  async function addInspiration() {
    if (!token || !imageUrl.trim()) return

    setIsSubmitting(true)
    setError('')
    try {
      const created = await api.addInspiration(token, {
        image_url: imageUrl.trim(),
        detected_tags: tagInput
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
      })
      setItems((current) => [created, ...current])
      setImageUrl('')
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : 'Unable to save inspiration.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Inspiration Board"
        title="Build the visual direction your home is leaning toward."
        description="ReFrame studies your saved references to understand mood, texture, materiality, light, and restraint."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <SurfaceCard>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <div key={item.id} className="rounded-[24px] bg-sand-50 p-3">
                <EditorialImage
                  src={item.image_url || editorialImages.inspirationA}
                  alt="Inspiration"
                  className="h-40 rounded-[18px]"
                />
                <p className="mt-3 break-all text-xs text-ink-500">{item.image_url}</p>
              </div>
            ))}
            <div className="rounded-[24px] border border-dashed border-sand-300 bg-white p-4">
              <input
                value={imageUrl}
                onChange={(event) => setImageUrl(event.target.value)}
                placeholder="https://example.com/inspiration.jpg"
                className="w-full rounded-2xl border border-sand-200 bg-surface px-4 py-3 text-sm outline-none"
              />
              <input
                value={tagInput}
                onChange={(event) => setTagInput(event.target.value)}
                placeholder="Warm lighting, Neutral colours"
                className="mt-3 w-full rounded-2xl border border-sand-200 bg-surface px-4 py-3 text-sm outline-none"
              />
              <button
                type="button"
                onClick={addInspiration}
                disabled={isSubmitting}
                className="mt-3 rounded-2xl bg-ink-900 px-4 py-3 text-sm font-medium text-white disabled:opacity-60"
              >
                {isSubmitting ? 'Saving...' : '+ Add Inspiration'}
              </button>
            </div>
          </div>
        </SurfaceCard>

        <SurfaceCard className="space-y-4">
          <p className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
            AI detected preferences
          </p>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-sand-50 px-3 py-2 text-sm text-ink-700"
              >
                {tag}
              </span>
            ))}
            {tags.length === 0 ? (
              <p className="text-sm text-ink-500">Add inspiration items to build preference tags.</p>
            ) : null}
          </div>
        </SurfaceCard>
      </div>
    </div>
  )
}
