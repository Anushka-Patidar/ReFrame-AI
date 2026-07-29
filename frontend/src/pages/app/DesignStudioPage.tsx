import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Camera, Home, ImagePlus, Ruler, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { EditorialImage } from '../../components/EditorialImage'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'

const roomOptions = ['Bedroom', 'Living Room', 'Kitchen', 'Bathroom', 'Balcony', 'Other']

export function DesignStudioPage() {
  const navigate = useNavigate()
  const { token } = useAuth()
  const [form, setForm] = useState({
    room_type: 'Bedroom',
    dimensions: { length: 14, width: 12, height: 10 },
    match_home_style: true,
  })
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [manualImageUrl, setManualImageUrl] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const previewUrl = useMemo(() => {
    if (selectedFile) {
      return URL.createObjectURL(selectedFile)
    }
    return manualImageUrl
  }, [manualImageUrl, selectedFile])

  useEffect(() => {
    return () => {
      if (selectedFile) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl, selectedFile])

  async function handleSubmit() {
    if (!token) return
    if (!selectedFile && !manualImageUrl.trim()) {
      setError('Upload or capture a room photo first. ReFrame needs your real space to redesign.')
      return
    }
    setError('')
    setIsSubmitting(true)
    try {
      const room = await api.createRoom(token, {
        ...form,
        original_image_url: manualImageUrl || undefined,
      })
      const finalRoom =
        selectedFile != null
          ? await api.uploadRoomImage(token, room.id, selectedFile)
          : room
      if (!finalRoom.original_image_url) {
        setError('Room photo was not saved. Please upload again.')
        return
      }
      navigate(`/app/design-studio/${finalRoom.id}/chat`)
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : 'Unable to create room.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="AI Design Studio"
        title="Begin with the room you already live in."
        description="A single photograph becomes a design conversation, a requirement plan, a space check, and a refined visual direction."
      />
      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <SurfaceCard className="overflow-hidden p-0">
          <div className="grid lg:grid-cols-[0.92fr_1.08fr]">
            <div className="flex flex-col justify-between gap-8 p-8 lg:p-10">
              <div className="space-y-6">
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.32em] text-accent-600">
                  Upload your space
                </p>
                <div className="space-y-4">
                  <h3 className="font-editorial text-5xl leading-[0.92] tracking-[-0.05em] text-ink-950">
                    Design around what already matters.
                  </h3>
                  <p className="max-w-lg text-sm leading-8 text-ink-500">
                    ReFrame doesn&apos;t ignore your existing room. It studies the room you
                    have, the pieces you want to preserve, and the mood you want to grow into.
                  </p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <StudioFact label="Room" value={form.room_type} />
                <StudioFact
                  label="Dimensions"
                  value={`${form.dimensions.length} × ${form.dimensions.width}`}
                />
                <StudioFact
                  label="Style Memory"
                  value={form.match_home_style ? 'Enabled' : 'Custom'}
                />
              </div>
            </div>
            <EditorialImage
              src={previewUrl || editorialImages.hero}
              alt="Studio preview"
              overlay
              className="min-h-[360px]"
            >
              <div className="flex h-full flex-col justify-between p-6 text-white">
                <div className="ml-auto flex gap-2">
                  {['Keep', 'Change', 'Remove'].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.2em] backdrop-blur"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="grid max-w-sm gap-3">
                  <div className="rounded-[1.2rem] border border-white/15 bg-white/10 p-4 backdrop-blur">
                    <p className="text-xs uppercase tracking-[0.24em] text-white/70">
                      Studio prompt
                    </p>
                    <p className="mt-3 text-sm leading-7 text-white/90">
                      “Preserve the soul of the room. Redesign the rest with calm,
                      intelligence, and warmth.”
                    </p>
                  </div>
                </div>
              </div>
            </EditorialImage>
          </div>
        </SurfaceCard>

        <div className="grid gap-6">
          <SurfaceCard className="space-y-6">
            <div className="grid gap-5">
              <label className="space-y-3">
                <span className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
                  Room image
                </span>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="flex cursor-pointer items-center justify-center gap-2 rounded-[1.3rem] border border-sand-200 bg-white/80 px-4 py-4 text-sm font-medium text-ink-900 transition hover:border-accent-500">
                    <ImagePlus className="h-4 w-4" />
                    Upload from device
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <label className="flex cursor-pointer items-center justify-center gap-2 rounded-[1.3rem] border border-sand-200 bg-white/80 px-4 py-4 text-sm font-medium text-ink-900 transition hover:border-accent-500">
                    <Camera className="h-4 w-4" />
                    Capture photo
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      className="hidden"
                      onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                </div>
                <input
                  value={manualImageUrl}
                  onChange={(event) => setManualImageUrl(event.target.value)}
                  placeholder="Optional fallback: paste an image URL"
                  className="w-full rounded-[1.3rem] border border-sand-200 bg-white/80 px-4 py-3 text-sm outline-none transition focus:border-accent-500"
                />
                {selectedFile ? (
                  <p className="text-sm text-ink-500">{selectedFile.name}</p>
                ) : null}
              </label>

              <div className="space-y-3">
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
                  Room type
                </p>
                <div className="grid grid-cols-2 gap-3">
                  {roomOptions.map((room) => (
                    <button
                      key={room}
                      type="button"
                      className={`rounded-[1.2rem] border px-4 py-3 text-sm transition ${
                        room === form.room_type
                          ? 'border-accent-500 bg-sand-25 text-ink-950'
                          : 'border-sand-200 bg-white/65 text-ink-500'
                      }`}
                      onClick={() =>
                        setForm((current) => ({
                          ...current,
                          room_type: room,
                        }))
                      }
                    >
                      {room}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Ruler className="h-4 w-4 text-accent-600" />
                  <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
                    Dimensions
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    ['Length', 'length'],
                    ['Width', 'width'],
                    ['Height', 'height'],
                  ].map(([label, key]) => (
                    <label key={label} className="space-y-2">
                      <span className="text-xs uppercase tracking-[0.18em] text-ink-500">
                        {label}
                      </span>
                      <input
                        type="number"
                        min={1}
                        value={form.dimensions[key as keyof typeof form.dimensions]}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            dimensions: {
                              ...current.dimensions,
                              [key]: Number(event.target.value),
                            },
                          }))
                        }
                        className="w-full rounded-[1.2rem] border border-sand-200 bg-white/80 px-4 py-3 text-sm outline-none transition focus:border-accent-500"
                      />
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between rounded-[1.5rem] border border-sand-200 bg-sand-25 px-5 py-4">
                <div className="flex items-center gap-3">
                  <Home className="h-5 w-5 text-accent-600" />
                  <div>
                    <p className="font-medium text-ink-900">Match my existing home style</p>
                    <p className="text-sm text-ink-500">
                      Keep this room aligned with your overall design memory.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setForm((current) => ({
                      ...current,
                      match_home_style: !current.match_home_style,
                    }))
                  }
                  className={`flex h-7 w-12 items-center rounded-full p-1 ${
                    form.match_home_style ? 'bg-ink-900' : 'bg-sand-300'
                  }`}
                >
                  <div
                    className={`h-5 w-5 rounded-full bg-white transition ${
                      form.match_home_style ? 'ml-auto' : ''
                    }`}
                  />
                </button>
              </div>

              {error ? <p className="text-sm text-red-600">{error}</p> : null}
            </div>
          </SurfaceCard>

          <SurfaceCard className="space-y-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full border border-sand-200 bg-sand-25 text-accent-600">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
                  What happens next
                </p>
                <p className="mt-2 font-editorial text-3xl tracking-[-0.04em] text-ink-950">
                  ReFrame will guide the room forward.
                </p>
              </div>
            </div>
            <div className="space-y-4 text-sm leading-7 text-ink-500">
              <p>01 Discuss style, priorities, constraints, and budget.</p>
              <p>02 Turn the conversation into a precise requirement plan.</p>
              <p>03 Run a practical space check before generating versions.</p>
            </div>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink-950 px-5 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:opacity-60"
            >
              {isSubmitting ? 'Creating Room...' : 'Continue to AI Discussion'}
              <ArrowRight className="h-4 w-4" />
            </button>
          </SurfaceCard>
        </div>
      </div>
    </div>
  )
}

function StudioFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] border border-sand-200/80 bg-sand-25 px-4 py-4">
      <p className="text-[0.65rem] uppercase tracking-[0.22em] text-ink-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-ink-900">{value}</p>
    </div>
  )
}
