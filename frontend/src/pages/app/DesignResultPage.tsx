import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Heart, MessageSquareMore, RefreshCcw, Sparkles } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { EditorialImage } from '../../components/EditorialImage'
import { GenerationProgress } from '../../components/GenerationProgress'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { DesignRequirements, DesignVersion, Room } from '../../types/api'

type QualityMode = 'preview' | 'balanced' | 'quality'

export function DesignResultPage() {
  const navigate = useNavigate()
  const { roomId = '', designId = '' } = useParams()
  const { token } = useAuth()
  const [room, setRoom] = useState<Room | null>(null)
  const [requirements, setRequirements] = useState<DesignRequirements | null>(null)
  const [designs, setDesigns] = useState<DesignVersion[]>([])
  const [error, setError] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [isRevising, setIsRevising] = useState(false)
  const [showRevise, setShowRevise] = useState(false)
  const [reviseDraft, setReviseDraft] = useState('')
  const [qualityMode, setQualityMode] = useState<QualityMode>(() => {
    if (typeof window === 'undefined') return 'balanced'
    const stored = window.localStorage.getItem('reframe-quality-mode')
    return stored === 'preview' || stored === 'quality' ? stored : 'balanced'
  })

  useEffect(() => {
    if (!token) return

    void Promise.all([
      api.getRoom(token, roomId),
      api.listDesigns(token, roomId),
      api.getRequirements(token, roomId),
    ])
      .then(([nextRoom, nextDesigns, nextRequirements]) => {
        setRoom(nextRoom)
        setDesigns(nextDesigns)
        setRequirements(nextRequirements)
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load generated design.',
        ),
      )
  }, [roomId, token])

  const activeDesign = designs.find((design) => design.id === designId) ?? designs[0] ?? null
  const beforeImage = room?.original_image_url || null
  const afterImage = activeDesign?.image_url || null
  const sameImageBug =
    Boolean(beforeImage && afterImage) &&
    beforeImage!.split('?')[0] === afterImage!.split('?')[0]

  useEffect(() => {
    if (sameImageBug) {
      setError(
        "Local generation couldn't complete — the result matched your original photo. Please retry.",
      )
    }
  }, [sameImageBug])

  async function generateAnother() {
    if (!token) return
    setError('')
    setIsGenerating(true)
    try {
      window.localStorage.setItem('reframe-quality-mode', qualityMode)
      try {
        const status = await api.getGenerationStatus()
        if (status.busy) {
          await api.resetGeneration()
        }
      } catch {
        // Ignore and continue.
      }
      const nextDesign = await api.generateDesign(token, roomId, qualityMode)
      if (
        room?.original_image_url &&
        nextDesign.image_url &&
        room.original_image_url.split('?')[0] === nextDesign.image_url.split('?')[0]
      ) {
        throw new Error(
          "Local generation couldn't complete — the result matched your original photo. Please retry.",
        )
      }
      setDesigns((current) => [...current, nextDesign])
      navigate(`/app/design-studio/${roomId}/result/${nextDesign.id}`)
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Local generation couldn't complete. Please retry."
      if (message.toLowerCase().includes('already in progress')) {
        try {
          await api.resetGeneration()
          setError('A stuck redesign was cleared. Click Generate Another again.')
        } catch {
          setError(message)
        }
      } else {
        setError(message)
      }
    } finally {
      setIsGenerating(false)
    }
  }

  async function submitRevision() {
    if (!token || !activeDesign || !reviseDraft.trim()) return
    setError('')
    setIsRevising(true)
    try {
      const nextDesign = await api.reviseDesign(token, roomId, activeDesign.id, {
        role: 'user',
        content: reviseDraft.trim(),
      })
      setDesigns((current) => [...current, nextDesign])
      setRequirements(await api.getRequirements(token, roomId))
      setReviseDraft('')
      setShowRevise(false)
      navigate(`/app/design-studio/${roomId}/result/${nextDesign.id}`)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to revise this design.',
      )
    } finally {
      setIsRevising(false)
    }
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Generated Design"
        title={activeDesign?.title ?? 'Generated Design'}
        description="Your original room stays the same. ReFrame applies only the style and changes you asked for — not a brand-new layout."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <GenerationProgress active={isGenerating || isRevising} />

      <div className="grid gap-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <SurfaceCard className="space-y-4 p-4">
            <div className="flex items-center justify-between px-2">
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.26em] text-accent-600">
                Original Room
              </p>
              <p className="text-xs text-ink-500">Before</p>
            </div>
            <EditorialImage
              src={room?.original_image_url || editorialImages.transformationBefore}
              alt="Original Room"
              fit="contain"
              className="h-[420px] rounded-[1.8rem]"
            >
              <div className="flex h-full items-end p-5">
                <span className="rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.2em] text-white backdrop-blur">
                  Before · {room?.room_type ?? 'Existing space'}
                </span>
              </div>
            </EditorialImage>
          </SurfaceCard>

          <SurfaceCard className="space-y-4 p-4">
            <div className="flex items-center justify-between px-2">
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.26em] text-accent-600">
                AI Design
              </p>
              <p className="text-xs text-ink-500">
                {activeDesign?.version ?? 'Pending render'}
              </p>
            </div>
            {activeDesign?.image_url && !sameImageBug ? (
              <EditorialImage
                src={`${activeDesign.image_url}${activeDesign.image_url.includes('?') ? '&' : '?'}v=${activeDesign.id}`}
                alt="AI Design"
                fit="contain"
                className="h-[420px] rounded-[1.8rem]"
              >
                <div className="flex h-full items-end justify-between gap-3 p-5">
                  <span className="rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.2em] text-white backdrop-blur">
                    After · {homeStyleLabel(activeDesign.title)}
                  </span>
                </div>
              </EditorialImage>
            ) : (
              <div className="flex h-[420px] flex-col justify-center gap-4 rounded-[1.8rem] border border-sand-200 bg-sand-25 p-6">
                  <p className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
                    Local generation couldn&apos;t complete.
                  </p>
                  <p className="max-w-md text-sm leading-7 text-ink-500">
                    ReFrame will not show your original photo as a fake AI result. Please retry when
                    you&apos;re ready.
                  </p>
                <button
                  type="button"
                  onClick={generateAnother}
                  disabled={isGenerating}
                  className="inline-flex w-fit items-center justify-center gap-2 rounded-full bg-ink-950 px-5 py-3 text-sm font-medium text-white disabled:opacity-60"
                >
                  <RefreshCcw className="h-4 w-4" />
                  {isGenerating ? 'Retrying...' : 'Retry Generation'}
                </button>
              </div>
            )}
            {activeDesign?.image_url && !sameImageBug ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <ResultFact label="Style" value={requirements?.style ?? 'Pending'} />
                <ResultFact
                  label="Palette"
                  value={requirements?.colours.join(', ') || 'Style default'}
                />
                <ResultFact
                  label="Keep"
                  value={requirements?.keep.join(', ') || 'Room structure'}
                />
                <ResultFact
                  label="Add / Remove"
                  value={
                    [
                      ...(requirements?.add.map((item) => `+ ${item}`) ?? []),
                      ...(requirements?.remove.map((item) => `− ${item}`) ?? []),
                    ].join(', ') || 'Style lighting and palette'
                  }
                />
              </div>
            ) : null}
            {activeDesign?.note ? (
              <p className="px-2 text-sm leading-7 text-ink-500">{activeDesign.note}</p>
            ) : null}
          </SurfaceCard>
        </div>

        {showRevise ? (
          <SurfaceCard className="space-y-4">
            <p className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
              Discuss changes
            </p>
            <p className="text-sm leading-7 text-ink-500">
              Describe what to adjust. ReFrame will revise this version while keeping the same room
              geometry.
            </p>
            <textarea
              value={reviseDraft}
              onChange={(event) => setReviseDraft(event.target.value)}
              rows={4}
              placeholder="Make the lighting warmer, add brown leather textures, keep the sofa and TV wall."
              className="w-full rounded-[1.2rem] border border-sand-200 bg-sand-25 px-4 py-3 text-sm leading-7 outline-none"
            />
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={submitRevision}
                disabled={isRevising || !reviseDraft.trim()}
                className="inline-flex rounded-full bg-ink-950 px-5 py-3 text-sm font-medium text-white disabled:opacity-60"
              >
                {isRevising ? 'Revising...' : 'Generate Revision'}
              </button>
              <button
                type="button"
                onClick={() => setShowRevise(false)}
                className="inline-flex rounded-full border border-sand-200 bg-white px-5 py-3 text-sm font-medium text-ink-700"
              >
                Cancel
              </button>
            </div>
          </SurfaceCard>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <SurfaceCard>
            <p className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
              Design History
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {designs.map((version) => (
                <Link
                  key={version.id}
                  to={`/app/design-studio/${roomId}/result/${version.id}`}
                  className="rounded-[1.5rem] border border-sand-200 bg-sand-25 p-4 transition hover:border-accent-500"
                >
                  {version.image_url ? (
                    <img
                      src={`${version.image_url}${version.image_url.includes('?') ? '&' : '?'}v=${version.id}`}
                      alt={version.title}
                      className="mb-4 h-36 w-full rounded-[1.1rem] object-cover"
                    />
                  ) : null}
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-ink-900">
                      {version.version} · {version.title}
                    </p>
                    {version.id === activeDesign?.id ? (
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-medium">
                        Active
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-ink-500">{version.note}</p>
                </Link>
              ))}
              {designs.length === 0 ? (
                <div className="rounded-[24px] bg-sand-50 p-4 text-sm text-ink-500">
                  Generate your first design to create version history.
                </div>
              ) : null}
            </div>
          </SurfaceCard>

          <SurfaceCard className="space-y-3">
            <div className="rounded-[1.3rem] border border-sand-200 bg-sand-25 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Next Generation</p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {[
                  ['preview', 'Quick'],
                  ['balanced', 'Balanced'],
                  ['quality', 'Best'],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setQualityMode(value as QualityMode)}
                    disabled={isGenerating || isRevising}
                    className={`rounded-full border px-3 py-2 text-xs font-medium transition ${
                      qualityMode === value
                        ? 'border-ink-900 bg-ink-900 text-white'
                        : 'border-sand-200 bg-white text-ink-700'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <ActionButton
              label="Discuss Changes"
              icon={<MessageSquareMore className="h-4 w-4" />}
              onClick={() => setShowRevise(true)}
            />
            <ActionButton label="Save Design" icon={<Heart className="h-4 w-4" />} />
            <ActionButton
              label={isGenerating ? 'Generating...' : 'Generate Another'}
              icon={<RefreshCcw className="h-4 w-4" />}
              onClick={generateAnother}
            />
            <ActionLink
              to={`/app/design-score?designId=${activeDesign?.id ?? ''}`}
              label="Design Score"
              icon={<Sparkles className="h-4 w-4" />}
            />
            <ActionLink
              to={`/app/contractor-briefs?designId=${activeDesign?.id ?? ''}`}
              label="Generate Contractor Brief"
              icon={<Sparkles className="h-4 w-4" />}
            />
          </SurfaceCard>
        </div>
      </div>
    </div>
  )
}

function homeStyleLabel(title?: string) {
  return title ? title.replace('Generated ', '') : 'AI proposal'
}

function ResultFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] border border-sand-200 bg-white/80 px-4 py-4">
      <p className="text-[0.65rem] uppercase tracking-[0.22em] text-ink-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-ink-900">{value}</p>
    </div>
  )
}

function ActionLink({
  to,
  label,
  icon,
}: {
  to: string
  label: string
  icon: ReactNode
}) {
  return (
    <Link
      to={to}
      className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-ink-900 px-4 py-3 text-sm font-medium text-white"
    >
      {icon}
      {label}
    </Link>
  )
}

function ActionButton({
  label,
  icon,
  onClick,
}: {
  label: string
  icon: ReactNode
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-sand-200 bg-white px-4 py-3 text-sm font-medium text-ink-700"
    >
      {icon}
      {label}
    </button>
  )
}
