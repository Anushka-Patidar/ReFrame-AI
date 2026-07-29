import { useEffect, useState } from 'react'
import { ArrowRight, Pencil } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { EditorialImage } from '../../components/EditorialImage'
import { GenerationProgress } from '../../components/GenerationProgress'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { DesignRequirements, Room, SpaceCheck } from '../../types/api'

const requirementKeys: Array<keyof Pick<
  DesignRequirements,
  'keep' | 'remove' | 'add' | 'colours' | 'avoid' | 'notes'
>> = ['keep', 'remove', 'add', 'colours', 'avoid', 'notes']

type RequirementListKey = (typeof requirementKeys)[number]

function parseListDraft(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function DesignPlanPage() {
  const navigate = useNavigate()
  const { roomId = '' } = useParams()
  const { token } = useAuth()
  const [requirements, setRequirements] = useState<DesignRequirements | null>(null)
  const [draftFields, setDraftFields] = useState<Record<RequirementListKey, string>>({
    keep: '',
    remove: '',
    add: '',
    colours: '',
    avoid: '',
    notes: '',
  })
  const [room, setRoom] = useState<Room | null>(null)
  const [spaceCheck, setSpaceCheck] = useState<SpaceCheck | null>(null)
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  useEffect(() => {
    if (!token) return

    void Promise.all([
      api.getRequirements(token, roomId),
      api.getSpaceCheck(token, roomId),
      api.getRoom(token, roomId),
    ])
      .then(([nextRequirements, nextSpaceCheck, nextRoom]) => {
        setRequirements(nextRequirements)
        setDraftFields({
          keep: nextRequirements.keep.join(', '),
          remove: nextRequirements.remove.join(', '),
          add: nextRequirements.add.join(', '),
          colours: nextRequirements.colours.join(', '),
          avoid: nextRequirements.avoid.join(', '),
          notes: nextRequirements.notes.join(', '),
        })
        setSpaceCheck(nextSpaceCheck)
        setRoom(nextRoom)
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load the requirement plan.',
        ),
      )
  }, [roomId, token])

  function commitDraftField(key: RequirementListKey) {
    const values = parseListDraft(draftFields[key] ?? '')
    setRequirements((current) =>
      current
        ? {
            ...current,
            [key]: values,
          }
        : current,
    )
    setDraftFields((current) => ({
      ...current,
      [key]: values.join(', '),
    }))
  }

  function buildRequirementsPayload(): DesignRequirements | null {
    if (!requirements) return null
    const next = { ...requirements }
    for (const key of requirementKeys) {
      next[key] = parseListDraft(draftFields[key] ?? '')
    }
    return next
  }

  async function saveRequirements() {
    const payload = buildRequirementsPayload()
    if (!token || !payload) return
    setError('')
    setIsSaving(true)
    try {
      setRequirements(payload)
      await api.updateRequirements(token, roomId, payload)
      const refreshedSpaceCheck = await api.getSpaceCheck(token, roomId)
      setSpaceCheck(refreshedSpaceCheck)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save requirements.')
    } finally {
      setIsSaving(false)
    }
  }

  async function generateRoom() {
    const payload = buildRequirementsPayload()
    if (!token || !payload) return
    if (!room?.original_image_url) {
      setError('This room has no uploaded photo. Go back to Design Studio and upload one.')
      return
    }
    setError('')
    setIsGenerating(true)
    try {
      setRequirements(payload)
      await api.updateRequirements(token, roomId, payload)
      const design = await api.generateDesign(token, roomId)
      navigate(`/app/design-studio/${roomId}/result/${design.id}`)
    } catch (generateError) {
      setError(
        generateError instanceof Error ? generateError.message : 'Unable to generate design.',
      )
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Requirements Card"
        title="Confirm what ReFrame understood before generation."
        description="This is the quality checkpoint that turns conversation into a trusted design brief."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <GenerationProgress active={isGenerating} />

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <SurfaceCard className="space-y-8 overflow-hidden p-0">
          <EditorialImage
            src={room?.original_image_url || editorialImages.living}
            alt="Design plan mood"
            overlay
            className="min-h-[240px]"
          >
            <div className="flex h-full flex-col justify-end p-6 text-white">
              <p className="text-xs uppercase tracking-[0.28em] text-white/70">
                ReFrame brief
              </p>
              <p className="mt-3 font-editorial text-4xl leading-none tracking-[-0.05em]">
                Your room is ready to become a precise plan.
              </p>
            </div>
          </EditorialImage>

          <div className="space-y-8 p-6 lg:p-8">
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="rounded-[1.5rem] border border-sand-200 bg-sand-25 p-4">
              <span className="text-xs uppercase tracking-[0.2em] text-ink-500">Room</span>
              <input
                value={requirements?.room ?? ''}
                onChange={(event) =>
                  setRequirements((current) =>
                    current ? { ...current, room: event.target.value } : current,
                  )
                }
                className="mt-3 w-full bg-transparent text-sm font-medium text-ink-900 outline-none"
              />
            </label>
            <label className="rounded-[1.5rem] border border-sand-200 bg-sand-25 p-4">
              <span className="text-xs uppercase tracking-[0.2em] text-ink-500">Style</span>
              <input
                value={requirements?.style ?? ''}
                onChange={(event) =>
                  setRequirements((current) =>
                    current ? { ...current, style: event.target.value } : current,
                  )
                }
                className="mt-3 w-full bg-transparent text-sm font-medium text-ink-900 outline-none"
              />
            </label>
            <label className="rounded-[1.5rem] border border-sand-200 bg-sand-25 p-4">
              <span className="text-xs uppercase tracking-[0.2em] text-ink-500">Budget</span>
              <input
                type="number"
                min={1000}
                value={requirements?.budget ?? 0}
                onChange={(event) =>
                  setRequirements((current) =>
                    current
                      ? { ...current, budget: Number(event.target.value) || 0 }
                      : current,
                  )
                }
                className="mt-3 w-full bg-transparent text-sm font-medium text-ink-900 outline-none"
              />
            </label>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {requirementKeys.map((key) => (
              <div key={key} className="rounded-[1.6rem] border border-sand-200 bg-white/75 p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
                  {key}
                </p>
                <p className="mt-2 text-xs text-ink-500">
                  Separate items with commas. Spaces are allowed while typing.
                </p>
                <textarea
                  value={draftFields[key] ?? ''}
                  onChange={(event) =>
                    setDraftFields((current) => ({
                      ...current,
                      [key]: event.target.value,
                    }))
                  }
                  onBlur={() => commitDraftField(key)}
                  rows={4}
                  placeholder="e.g. warm lighting, soft rug, wall art"
                  className="mt-4 w-full rounded-[1.2rem] border border-sand-200 bg-sand-25 px-4 py-3 text-sm leading-7 text-ink-700 outline-none"
                />
              </div>
            ))}
          </div>
          </div>
        </SurfaceCard>

        <div className="space-y-6">
          <SurfaceCard className="space-y-4">
            <p className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
              Space check
            </p>
            <div className="space-y-3 text-sm leading-7 text-ink-500">
              <p>Room size: {spaceCheck?.room_size ?? 'Loading...'}</p>
              {spaceCheck?.checks.map((check) => (
                <p key={check.item}>
                  {check.item}: {check.note}
                </p>
              ))}
              {spaceCheck ? <p>{spaceCheck.recommendation}</p> : null}
            </div>
          </SurfaceCard>

          <SurfaceCard className="space-y-4">
            <button
              type="button"
              onClick={saveRequirements}
              disabled={isSaving}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-sand-200 bg-white px-4 py-3 text-sm font-medium text-ink-700 transition hover:-translate-y-0.5"
            >
              <Pencil className="h-4 w-4" />
              {isSaving ? 'Saving...' : 'Save Requirements'}
            </button>
            <button
              type="button"
              onClick={generateRoom}
              disabled={isGenerating}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink-950 px-4 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5"
            >
              {isGenerating ? 'Generating your redesign...' : 'Generate My Room'}
              <ArrowRight className="h-4 w-4" />
            </button>
          </SurfaceCard>
        </div>
      </div>
    </div>
  )
}
