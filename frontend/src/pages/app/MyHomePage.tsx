import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EditorialImage } from '../../components/EditorialImage'
import { EmptyState } from '../../components/EmptyState'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { HomeProfile, Room } from '../../types/api'

export function MyHomePage() {
  const { token } = useAuth()
  const [home, setHome] = useState<HomeProfile | null>(null)
  const [rooms, setRooms] = useState<Room[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return

    void Promise.all([api.getHome(token), api.listRooms(token)])
      .then(([nextHome, nextRooms]) => {
        setHome(nextHome)
        setRooms(nextRooms)
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error ? requestError.message : 'Unable to load home data.',
        ),
      )
  }, [token])

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="My Home"
        title="A home held together by one evolving language."
        description="ReFrame tracks materiality, light, colour, and room decisions so each space belongs to the same story."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <SurfaceCard className="space-y-6 overflow-hidden p-0">
          <EditorialImage
            src={editorialImages.living}
            alt="Home style"
            overlay
            className="min-h-[280px]"
          >
            <div className="flex h-full flex-col justify-end p-6 text-white">
              <p className="text-xs uppercase tracking-[0.26em] text-white/70">Your home style</p>
              <p className="mt-3 font-editorial text-5xl leading-[0.92] tracking-[-0.05em]">
                {home?.overall_style_profile.style ?? 'Warm Minimal Luxury'}
              </p>
            </div>
          </EditorialImage>
          <div className="grid gap-3 p-6 text-sm text-ink-500">
            <p>Main colours: {home?.overall_style_profile.colours.join(', ') ?? '-'}</p>
            <p>Lighting: {home?.overall_style_profile.lighting ?? '-'}</p>
            <p>Wood: {home?.overall_style_profile.wood ?? '-'}</p>
            <p>Metal finish: {home?.overall_style_profile.metal_finish ?? '-'}</p>
          </div>
        </SurfaceCard>
        <SurfaceCard className="space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
                Rooms in your home
              </p>
              <p className="mt-3 font-editorial text-4xl tracking-[-0.04em] text-ink-950">
                Home Story
              </p>
            </div>
            <Link
              to="/app/design-studio"
              className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white/70 px-5 py-3 text-sm font-medium text-ink-900"
            >
              <Plus className="h-4 w-4" />
              Add Room
            </Link>
          </div>
          {rooms.length === 0 ? (
            <EmptyState
              title="Your home grows one room at a time."
              description="Start with one photographed room to unlock style continuity across the full home."
              actionLabel="Add Your First Room"
              actionHref="/app/design-studio"
              imageSrc={editorialImages.bedroom}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {rooms.map((room, index) => (
                <Link
                  key={room.id}
                  to={`/app/design-studio/${room.id}/plan`}
                  className="overflow-hidden rounded-[1.7rem] border border-sand-200 bg-white/75 transition duration-300 hover:-translate-y-1"
                >
                  <EditorialImage
                    src={
                      room.original_image_url ||
                      [editorialImages.bedroom, editorialImages.living, editorialImages.kitchen, editorialImages.study][
                        index % 4
                      ]
                    }
                    alt={room.room_type}
                    className="h-44"
                  />
                  <div className="space-y-3 p-4">
                    <p className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
                      {room.room_type}
                    </p>
                    <div className="flex items-center justify-between text-sm text-ink-500">
                      <span>{room.status}</span>
                      <span>{home?.preferred_style ?? 'Warm Minimal'}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </SurfaceCard>
      </div>
    </div>
  )
}
