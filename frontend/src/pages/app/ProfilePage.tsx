import { useEffect, useState } from 'react'
import { Pencil, Save } from 'lucide-react'
import { EditorialImage } from '../../components/EditorialImage'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { HomeProfile, SessionUser } from '../../types/api'

export function ProfilePage() {
  const { token } = useAuth()
  const [user, setUser] = useState<SessionUser | null>(null)
  const [home, setHome] = useState<HomeProfile | null>(null)
  const [profileDraft, setProfileDraft] = useState({ name: '', phone: '', city: '' })
  const [homeDraft, setHomeDraft] = useState({
    property_type: '',
    rooms: 0,
    preferred_style: '',
    overall_style_profile: {
      style: '',
      colours: [] as string[],
      lighting: '',
      wood: '',
      metal_finish: '',
    },
  })
  const [editingProfile, setEditingProfile] = useState(false)
  const [editingHome, setEditingHome] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return

    void Promise.all([api.getProfile(token), api.getHome(token)])
      .then(([nextUser, nextHome]) => {
        setUser(nextUser)
        setHome(nextHome)
        setProfileDraft({
          name: nextUser.name,
          phone: nextUser.phone,
          city: nextUser.city,
        })
        setHomeDraft({
          property_type: nextHome.property_type,
          rooms: nextHome.rooms,
          preferred_style: nextHome.preferred_style,
          overall_style_profile: nextHome.overall_style_profile,
        })
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error ? requestError.message : 'Unable to load profile.',
        ),
      )
  }, [token])

  async function saveProfile() {
    if (!token) return
    await api.updateProfile(token, profileDraft)
    setUser((current) =>
      current ? { ...current, ...profileDraft } : current,
    )
    setEditingProfile(false)
  }

  async function saveHome() {
    if (!token || !home) return
    await api.updateHome(token, homeDraft)
    setHome({
      ...home,
      ...homeDraft,
    })
    setEditingHome(false)
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Profile"
        title="The client profile behind the home."
        description="Identity, location, and the foundational preferences that ReFrame uses to personalize every design decision."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <SurfaceCard className="space-y-4 overflow-hidden p-0">
          <EditorialImage
            src={editorialImages.study}
            alt="Profile cover"
            className="min-h-[260px]"
          />
          <div className="space-y-4 p-6">
            <p className="font-editorial text-4xl tracking-[-0.04em] text-ink-950">
              {user?.name ?? 'Your Profile'}
            </p>
            <p className="text-sm leading-7 text-ink-500">
              {user?.city ?? 'Location'} • ReFrame project owner
            </p>
          </div>
        </SurfaceCard>
        <div className="grid gap-6">
          <SurfaceCard className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-lg font-semibold text-ink-900">Personal Details</p>
              <button
                type="button"
                onClick={() => (editingProfile ? void saveProfile() : setEditingProfile(true))}
                className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white/70 px-4 py-2 text-sm font-medium text-ink-900"
              >
                {editingProfile ? <Save className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                {editingProfile ? 'Save' : 'Edit'}
              </button>
            </div>
            <div className="grid gap-3 text-sm text-ink-500">
              <label className="space-y-2">
                <span>Name</span>
                <input
                  value={profileDraft.name}
                  onChange={(event) =>
                    setProfileDraft((current) => ({ ...current, name: event.target.value }))
                  }
                  disabled={!editingProfile}
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 outline-none disabled:opacity-70"
                />
              </label>
              <label className="space-y-2">
                <span>Location</span>
                <input
                  value={profileDraft.city}
                  onChange={(event) =>
                    setProfileDraft((current) => ({ ...current, city: event.target.value }))
                  }
                  disabled={!editingProfile}
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 outline-none disabled:opacity-70"
                />
              </label>
              <label className="space-y-2">
                <span>Email</span>
                <input
                  value={user?.email ?? ''}
                  disabled
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 opacity-70 outline-none"
                />
              </label>
              <label className="space-y-2">
                <span>Phone</span>
                <input
                  value={profileDraft.phone}
                  onChange={(event) =>
                    setProfileDraft((current) => ({ ...current, phone: event.target.value }))
                  }
                  disabled={!editingProfile}
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 outline-none disabled:opacity-70"
                />
              </label>
            </div>
          </SurfaceCard>
          <SurfaceCard className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-lg font-semibold text-ink-900">My Home</p>
              <button
                type="button"
                onClick={() => (editingHome ? void saveHome() : setEditingHome(true))}
                className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white/70 px-4 py-2 text-sm font-medium text-ink-900"
              >
                {editingHome ? <Save className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                {editingHome ? 'Save' : 'Edit'}
              </button>
            </div>
            <div className="grid gap-3 text-sm text-ink-500">
              <label className="space-y-2">
                <span>Property Type</span>
                <input
                  value={homeDraft.property_type}
                  onChange={(event) =>
                    setHomeDraft((current) => ({
                      ...current,
                      property_type: event.target.value,
                    }))
                  }
                  disabled={!editingHome}
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 outline-none disabled:opacity-70"
                />
              </label>
              <label className="space-y-2">
                <span>Rooms</span>
                <input
                  type="number"
                  min={1}
                  value={homeDraft.rooms}
                  onChange={(event) =>
                    setHomeDraft((current) => ({
                      ...current,
                      rooms: Number(event.target.value),
                    }))
                  }
                  disabled={!editingHome}
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 outline-none disabled:opacity-70"
                />
              </label>
              <label className="space-y-2">
                <span>Preferred Style</span>
                <input
                  value={homeDraft.preferred_style}
                  onChange={(event) =>
                    setHomeDraft((current) => ({
                      ...current,
                      preferred_style: event.target.value,
                    }))
                  }
                  disabled={!editingHome}
                  className="w-full rounded-[1.1rem] border border-sand-200 bg-sand-25 px-4 py-3 outline-none disabled:opacity-70"
                />
              </label>
            </div>
          </SurfaceCard>
        </div>
      </div>
    </div>
  )
}
