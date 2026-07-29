import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../lib/api'
import type { RegionConstraint, Room } from '../../types/api'
import { RegionMaskEditor } from '../../components/RegionMaskEditor'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'

export function RoomMaskEditorPage() {
  const navigate = useNavigate()
  const { roomId = '' } = useParams()
  const { token } = useAuth()

  const [room, setRoom] = useState<Room | null>(null)
  const [constraints, setConstraints] = useState<RegionConstraint[]>([])
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function refresh() {
    if (!token) return
    setIsLoading(true)
    try {
      const [nextRoom, nextConstraints] = await Promise.all([
        api.getRoom(token, roomId),
        api.listRegionConstraints(token, roomId),
      ])
      setRoom(nextRoom)
      setConstraints(nextConstraints)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load region constraints.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!token) return
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId, token])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-sand-200 bg-white hover:bg-sand-25"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="font-editorial text-3xl tracking-[-0.04em] text-ink-950">
          Mark Room Elements
        </h1>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <SurfaceCard className="space-y-6 overflow-hidden p-6 lg:p-8">
        <SectionHeader
          eyebrow="Region Mask Editor"
          title="KEEP / CHANGE / REMOVE"
          description="Paint areas on your real room photo. Masks are stored separately and will be used by future masked editors."
        />

        {!room?.original_image_url ? (
          <p className="text-sm text-ink-500">
            This room has no uploaded photo yet. Go to Design Studio and upload an image first.
          </p>
        ) : (
          <RegionMaskEditor
            token={token || ''}
            roomId={roomId}
            imageUrl={room.original_image_url}
            initialConstraints={constraints}
            onRefresh={refresh}
          />
        )}

        {isLoading ? <p className="text-sm text-ink-500">Loading...</p> : null}
      </SurfaceCard>
    </div>
  )
}

