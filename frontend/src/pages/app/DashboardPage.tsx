import { useEffect, useState } from 'react'
import {
  ArrowRight,
  BrainCircuit,
  Heart,
  NotebookPen,
  Plus,
  Sparkles,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { SurfaceCard } from '../../components/Cards'
import { EditorialImage } from '../../components/EditorialImage'
import { EmptyState } from '../../components/EmptyState'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type {
  DashboardSummary,
  DesignRequirements,
  HomeProfile,
  Inspiration,
  Room,
} from '../../types/api'

const quickActions = [
  {
    label: 'Design New Room',
    body: 'Start from one photograph and build a guided redesign.',
    icon: Sparkles,
    href: '/app/design-studio',
    tone: 'dark',
  },
  {
    label: 'Upload Inspiration',
    body: 'Teach ReFrame what calm, warm, and aspirational mean to you.',
    icon: Heart,
    href: '/app/inspiration',
    tone: 'light',
  },
  {
    label: 'Generate Contractor Brief',
    body: 'Translate a chosen version into practical execution notes.',
    icon: NotebookPen,
    href: '/app/contractor-briefs',
    tone: 'outline',
  },
  {
    label: 'Find a Professional',
    body: 'Discover local designers, carpenters, and specialists.',
    icon: Users,
    href: '/app/professionals',
    tone: 'image',
  },
]

export function DashboardPage() {
  const { token, user } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [home, setHome] = useState<HomeProfile | null>(null)
  const [rooms, setRooms] = useState<Room[]>([])
  const [inspirations, setInspirations] = useState<Inspiration[]>([])
  const [roomBudgets, setRoomBudgets] = useState<Record<string, number>>({})
  const [roomVersions, setRoomVersions] = useState<Record<string, number>>({})
  const [leadRequirements, setLeadRequirements] = useState<DesignRequirements | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return

    void Promise.all([
      api.getDashboard(token),
      api.getHome(token),
      api.listRooms(token),
      api.listInspirations(token),
    ])
      .then(async ([nextSummary, nextHome, nextRooms, nextInspirations]) => {
        setSummary(nextSummary)
        setHome(nextHome)
        setRooms(nextRooms)
        setInspirations(nextInspirations)

        if (nextRooms.length === 0) {
          setRoomBudgets({})
          setRoomVersions({})
          setLeadRequirements(null)
          return
        }

        const roomMeta = await Promise.all(
          nextRooms.map(async (room) => {
            const [requirements, designs] = await Promise.all([
              api.getRequirements(token, room.id),
              api.listDesigns(token, room.id),
            ])

            return {
              roomId: room.id,
              budget: requirements.budget,
              versions: designs.length,
              requirements,
            }
          }),
        )

        setRoomBudgets(
          Object.fromEntries(roomMeta.map((entry) => [entry.roomId, entry.budget])),
        )
        setRoomVersions(
          Object.fromEntries(roomMeta.map((entry) => [entry.roomId, entry.versions])),
        )
        setLeadRequirements(roomMeta[0]?.requirements ?? null)
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load dashboard right now.',
        ),
      )
  }, [token])

  const inspirationTags = [...new Set(inspirations.flatMap((item) => item.detected_tags))]
  const styleTags = [
    ...(home?.overall_style_profile.colours ?? []),
    ...(home?.overall_style_profile.lighting ? [home.overall_style_profile.lighting] : []),
    ...(home?.overall_style_profile.wood ? [home.overall_style_profile.wood] : []),
    ...(home?.overall_style_profile.metal_finish ? [home.overall_style_profile.metal_finish] : []),
    ...inspirationTags,
  ]
  const uniqueStyleTags = [...new Set(styleTags)].filter(Boolean)
  const transformationCards = rooms.slice(0, 2)

  const plannedBudget = Math.round((summary?.estimated_budget ?? 0) * 0.63)
  const remainingBudget = Math.max((summary?.estimated_budget ?? 0) - plannedBudget, 0)
  const budgetProgress =
    summary?.estimated_budget && summary.estimated_budget > 0
      ? Math.min((plannedBudget / summary.estimated_budget) * 100, 100)
      : 0
  const scoreValue = summary?.average_design_score ?? 0
  const heroVersionCount = rooms[0] ? roomVersions[rooms[0].id] ?? 0 : 0

  return (
    <div className="space-y-10 lg:space-y-12">
      <SectionHeader
        eyebrow="ReFrame Dashboard"
        title={summary?.greeting ?? `Good Morning, ${user?.name.split(' ')[0] ?? 'there'}`}
        description={
          summary?.summary ??
          'Let’s design your dream home with an AI-guided workflow that keeps every room connected.'
        }
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <SurfaceCard className="overflow-hidden p-0">
          <div className="grid lg:grid-cols-[0.95fr_1.05fr]">
            <div className="flex flex-col justify-between gap-8 p-8 lg:p-10">
              <div className="space-y-6">
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.34em] text-accent-600">
                  AI Design Studio
                </p>
                <div className="space-y-4">
                  <h3 className="font-editorial max-w-xl text-5xl leading-[0.92] tracking-[-0.05em] text-ink-950">
                    Reimagine the room you already love.
                  </h3>
                  <p className="max-w-lg text-sm leading-8 text-ink-500">
                    ReFrame preserves what matters, redesigns what doesn&apos;t, and
                    keeps your home evolving as one calm and coherent story.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  to="/app/design-studio"
                  className="inline-flex items-center gap-2 rounded-full bg-ink-950 px-6 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5"
                >
                  Design a Room
                  <ArrowRight className="h-4 w-4" />
                </Link>
                {rooms[0] ? (
                  <Link
                    to={`/app/design-studio/${rooms[0].id}/plan`}
                    className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white/70 px-6 py-3 text-sm font-medium text-ink-900 transition hover:-translate-y-0.5"
                  >
                    Continue Last Project
                  </Link>
                ) : null}
              </div>
            </div>

            <EditorialImage
              src={rooms[0]?.original_image_url || editorialImages.hero}
              alt="Featured interior"
              overlay
              className="min-h-[360px] lg:min-h-full"
            >
              <div className="flex h-full flex-col justify-between p-6 text-white">
                <div className="ml-auto flex flex-wrap justify-end gap-2">
                  {[
                    home?.overall_style_profile.style ?? 'Design Memory',
                    summary?.estimated_budget
                      ? `₹${(summary.estimated_budget / 100000).toFixed(1)}L Budget`
                      : 'Budget adapts as you design',
                    rooms.length ? `${rooms.length} Rooms` : 'Start with one room',
                  ].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.2em] backdrop-blur"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="space-y-3">
                  <p className="text-xs uppercase tracking-[0.28em] text-white/70">
                    {rooms[0]?.room_type ?? 'Your first room'}
                  </p>
                  <div className="grid max-w-sm grid-cols-2 gap-3">
                    <HeroFact label="Style" value={home?.preferred_style ?? 'Adaptive'} />
                    <HeroFact label="Versions" value={`${heroVersionCount || 0}`} />
                    <HeroFact label="Status" value={rooms[0]?.status ?? 'Ready'} />
                    <HeroFact label="AI Memory" value={`${uniqueStyleTags.length} signals`} />
                  </div>
                </div>
              </div>
            </EditorialImage>
          </div>
        </SurfaceCard>

        <div className="grid gap-6">
          <SurfaceCard className="relative overflow-hidden">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.3em] text-accent-600">
              Home Design Score
            </p>
            {scoreValue > 0 ? (
              <div className="mt-6 flex items-end gap-6">
                <div className="flex h-40 w-40 items-center justify-center rounded-full border border-sand-200 bg-[radial-gradient(circle_at_top,rgba(138,104,77,0.22),transparent_62%)]">
                  <div className="flex h-28 w-28 items-center justify-center rounded-full border border-sand-200 bg-white/80 text-center">
                    <div>
                      <p className="font-editorial text-5xl leading-none text-ink-950">
                        {scoreValue}
                      </p>
                      <p className="mt-2 text-[0.65rem] uppercase tracking-[0.24em] text-ink-500">
                        overall
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex-1 space-y-4">
                  {[
                    { label: 'Style Consistency', value: home ? Math.min(scoreValue + 4, 96) : scoreValue },
                    { label: 'Budget Alignment', value: home ? Math.min(scoreValue + 7, 98) : scoreValue },
                    { label: 'Space Harmony', value: scoreValue > 0 ? Math.max(scoreValue - 5, 65) : scoreValue },
                  ].map(({ label, value }) => (
                    <ProgressStat key={label} label={label} value={value} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-[1.5rem] border border-sand-200 bg-sand-25 p-5 text-sm leading-7 text-ink-500">
                Your design score appears after your first generated room.
              </div>
            )}
          </SurfaceCard>

          <SurfaceCard className="space-y-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.3em] text-accent-600">
                  Budget Intelligence
                </p>
                {summary?.estimated_budget ? (
                  <>
                    <p className="mt-3 font-editorial text-5xl leading-none text-ink-950">
                      ₹{(summary.estimated_budget / 100000).toFixed(1)}L
                    </p>
                    <p className="mt-2 text-sm text-ink-500">Estimated Home Budget</p>
                  </>
                ) : (
                  <>
                    <p className="mt-3 font-editorial text-4xl leading-none text-ink-950">
                      Budget begins with one designed room.
                    </p>
                    <p className="mt-2 text-sm text-ink-500">
                      Start your first room to build financial intelligence across the home.
                    </p>
                  </>
                )}
              </div>
              {summary?.estimated_budget ? (
                <div className="min-w-32 rounded-[1.5rem] bg-sand-25 p-4 text-right">
                  <p className="text-sm text-ink-500">Remaining</p>
                  <p className="mt-2 font-editorial text-3xl text-ink-900">
                    ₹{remainingBudget.toLocaleString('en-IN')}
                  </p>
                </div>
              ) : null}
            </div>
            {summary?.estimated_budget ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm text-ink-500">
                  <span>Planned</span>
                  <span>₹{plannedBudget.toLocaleString('en-IN')}</span>
                </div>
                <div className="h-2 rounded-full bg-sand-100">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-accent-600 to-accent-500 transition-all duration-700"
                    style={{ width: `${budgetProgress}%` }}
                  />
                </div>
                <p className="text-sm text-ink-500">Within your planned range.</p>
              </div>
            ) : null}
          </SurfaceCard>
        </div>
      </div>

      <SurfaceCard className="space-y-7">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeader
            eyebrow="My Home"
            title="One home. One evolving design language."
            description="Every room moves independently, but ReFrame keeps the whole home emotionally and visually connected."
          />
          <Link
            to="/app/design-studio"
            className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white/80 px-5 py-3 text-sm font-medium text-ink-900 transition hover:-translate-y-0.5"
          >
            <Plus className="h-4 w-4" />
            Add Room
          </Link>
        </div>

        {rooms.length === 0 ? (
          <EmptyState
            title="Your home story begins with one photograph."
            description="Start with your first room to unlock home-wide style memory, budget intelligence, and room-to-room consistency."
            actionLabel="Design Your First Room"
            actionHref="/app/design-studio"
            imageSrc={editorialImages.living}
          />
        ) : (
          <div className="grid gap-5 xl:grid-cols-4">
            {rooms.map((room, index) => (
              <Link
                key={room.id}
                to={`/app/design-studio/${room.id}/plan`}
                className="group overflow-hidden rounded-[2rem] border border-sand-200/80 bg-white/85 shadow-[var(--shadow-soft)] transition duration-300 hover:-translate-y-1"
              >
                <EditorialImage
                  src={
                    room.original_image_url ||
                    [editorialImages.bedroom, editorialImages.living, editorialImages.kitchen, editorialImages.study][
                      index % 4
                    ]
                  }
                  alt={room.room_type}
                  className="h-52"
                />
                <div className="space-y-4 p-5">
                  <div>
                    <p className="text-[0.7rem] uppercase tracking-[0.28em] text-accent-600">
                      {room.status}
                    </p>
                    <p className="mt-3 font-editorial text-3xl leading-none tracking-[-0.04em] text-ink-950">
                      {room.room_type}
                    </p>
                    <p className="mt-2 text-sm text-ink-500">
                      {home?.overall_style_profile.style ?? 'Warm Minimal Luxury'}
                    </p>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-xs text-ink-500">
                    <MiniStat label="Score" value={scoreValue ? `${scoreValue}` : 'Pending'} />
                    <MiniStat
                      label="Budget"
                      value={
                        roomBudgets[room.id]
                          ? `₹${Math.round(roomBudgets[room.id] / 1000)}K`
                          : 'Not set'
                      }
                    />
                    <MiniStat label="Versions" value={`${roomVersions[room.id] ?? 0}`} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </SurfaceCard>

      <SurfaceCard className="space-y-6">
        <SectionHeader
          eyebrow="Your Design Journey"
          title="A guided process from photograph to build-ready brief."
          description="ReFrame feels less like an image generator and more like a calm design companion with memory, structure, and next steps."
        />
        <div className="grid gap-3 lg:grid-cols-7">
          {['Upload', 'Discuss', 'Define', 'Generate', 'Refine', 'Finalize', 'Build'].map(
            (stage, index) => {
              const activeIndex = rooms.length > 0 ? 4 : 1
              const isComplete = index < activeIndex
              const isActive = index === activeIndex
              return (
                <div
                  key={stage}
                  className={`rounded-[1.5rem] border px-4 py-5 transition ${
                    isActive
                      ? 'border-accent-500 bg-sand-25'
                      : isComplete
                        ? 'border-sand-200 bg-white/70'
                        : 'border-dashed border-sand-200 bg-transparent'
                  }`}
                >
                  <p className="text-[0.7rem] uppercase tracking-[0.28em] text-accent-600">
                    0{index + 1}
                  </p>
                  <p className="mt-4 font-medium text-ink-900">{stage}</p>
                </div>
              )
            },
          )}
        </div>
      </SurfaceCard>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <SurfaceCard className="space-y-7">
          <SectionHeader
            eyebrow="Recent Transformations"
            title="Before and after, grounded in your real home."
            description="Each transformation keeps the story of the original room while making the outcome feel more elevated, calm, and aligned."
          />
          {transformationCards.length === 0 ? (
            <EmptyState
              title="Transformations appear after your first room is generated."
              description="Generate at least one room and ReFrame will start documenting the visual before-and-after story of your home."
              actionLabel="Start Designing"
              actionHref="/app/design-studio"
              imageSrc={editorialImages.transformationAfter}
            />
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              {transformationCards.map((room, index) => (
              <div
                key={room.id}
                className="overflow-hidden rounded-[1.8rem] border border-sand-200/80 bg-white/70"
              >
                <div className="grid grid-cols-2">
                  <EditorialImage
                    src={room.original_image_url || editorialImages.transformationBefore}
                    alt={`${room.room_type} before`}
                    className="h-56"
                  />
                  <EditorialImage
                    src={index % 2 === 0 ? editorialImages.transformationAfter : editorialImages.hero}
                    alt={`${room.room_type} after`}
                    className="h-56"
                  />
                </div>
                <div className="space-y-4 p-5">
                  <div>
                    <p className="text-[0.7rem] uppercase tracking-[0.28em] text-accent-600">
                      Version {String(roomVersions[room.id] ?? index + 1).padStart(2, '0')}
                    </p>
                    <p className="mt-3 font-editorial text-3xl leading-none tracking-[-0.04em] text-ink-950">
                      {room.room_type}
                    </p>
                    <p className="mt-2 text-sm text-ink-500">
                      {home?.overall_style_profile.style ?? 'Warm Minimal Luxury'}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Link
                      to={`/app/design-studio/${room.id}/plan`}
                      className="rounded-full border border-sand-200 bg-white px-4 py-2 text-sm font-medium text-ink-900"
                    >
                      View Project
                    </Link>
                    <Link
                      to={`/app/design-studio/${room.id}/chat`}
                      className="rounded-full bg-ink-950 px-4 py-2 text-sm font-medium text-white"
                    >
                      Create Version
                    </Link>
                  </div>
                </div>
              </div>
              ))}
            </div>
          )}
        </SurfaceCard>

        <div className="grid gap-6">
          <SurfaceCard className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-sand-200 bg-sand-25 text-accent-600">
                <BrainCircuit className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.3em] text-accent-600">
                  AI Design Memory
                </p>
                <p className="mt-2 font-editorial text-3xl tracking-[-0.04em] text-ink-950">
                  ReFrame remembers your taste.
                </p>
              </div>
            </div>
            <p className="text-sm leading-7 text-ink-500">
              {uniqueStyleTags.length > 0
                ? `Based on ${uniqueStyleTags.length} preferences inferred across your home.`
                : 'Your design memory starts after the first room and inspiration decisions are saved.'}
            </p>
            {uniqueStyleTags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {uniqueStyleTags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-sand-200 bg-white/80 px-3 py-2 text-sm text-ink-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            ) : (
              <div className="rounded-[1.5rem] border border-sand-200 bg-sand-25 p-4 text-sm text-ink-500">
                Upload inspiration or finalize a room to begin building your design memory.
              </div>
            )}
          </SurfaceCard>

          <SurfaceCard className="space-y-6">
            <div>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.3em] text-accent-600">
                What ReFrame knows about your home
              </p>
              <p className="mt-3 font-editorial text-3xl tracking-[-0.04em] text-ink-950">
                Keep. Change. Remove.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <KnowledgeColumn label="Keep" items={leadRequirements?.keep ?? []} />
              <KnowledgeColumn label="Change" items={leadRequirements?.add ?? []} />
              <KnowledgeColumn label="Remove" items={leadRequirements?.remove ?? []} />
            </div>
          </SurfaceCard>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SurfaceCard className="space-y-7">
          <SectionHeader
            eyebrow="Your Design Direction"
            title="A visual strip of the moods your home is leaning toward."
            description="Saved inspiration, natural materials, and room decisions merge into an evolving creative direction."
          />
          {inspirations.length === 0 ? (
            <EmptyState
              title="Build your visual language."
              description="Saved references sharpen ReFrame’s sense of colour, materiality, and calm. Add a few images to make the AI more personal."
              actionLabel="Explore Inspiration"
              actionHref="/app/inspiration"
              imageSrc={editorialImages.inspirationA}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
              <EditorialImage
                src={inspirations[0]?.image_url || editorialImages.inspirationA}
                alt="Inspiration feature"
                className="min-h-[320px] rounded-[1.8rem]"
              />
              <div className="grid gap-4">
                {[editorialImages.inspirationB, editorialImages.inspirationC].map((image) => (
                  <EditorialImage
                    key={image}
                    src={image}
                    alt="Inspiration detail"
                    className="min-h-[152px] rounded-[1.6rem]"
                  />
                ))}
              </div>
            </div>
          )}
        </SurfaceCard>

        <SurfaceCard className="space-y-7">
          <SectionHeader
            eyebrow="Quick Actions"
            title="Move your project forward."
            description="Editorial, visual, and practical next steps for the home you are shaping."
          />
          <div className="grid gap-4 md:grid-cols-2">
            {quickActions.map(({ label, body, icon: ActionIcon, href, tone }, index) => (
              <Link
                key={label}
                to={href}
                className={`group relative overflow-hidden rounded-[1.75rem] border p-5 transition duration-300 hover:-translate-y-1 ${
                  tone === 'dark'
                    ? 'border-ink-950 bg-ink-950 text-white'
                    : tone === 'image'
                      ? 'border-sand-200 text-white'
                      : tone === 'outline'
                        ? 'border-sand-200 bg-transparent text-ink-900'
                        : 'border-sand-200 bg-white/75 text-ink-900'
                } ${index === 0 ? 'md:col-span-2' : ''}`}
              >
                {tone === 'image' ? (
                  <EditorialImage
                    src={editorialImages.living}
                    alt={label}
                    overlay
                    className="absolute inset-0"
                  />
                ) : null}
                <div className="relative z-10 flex h-full flex-col justify-between gap-8">
                  <div className="flex items-center justify-between">
                    <span
                      className={`inline-flex h-11 w-11 items-center justify-center rounded-full ${
                        tone === 'dark'
                          ? 'bg-white/10'
                          : tone === 'image'
                            ? 'bg-white/15 backdrop-blur'
                            : 'border border-sand-200 bg-sand-25'
                      }`}
                    >
                      <ActionIcon className="h-5 w-5" />
                    </span>
                    <ArrowRight className="h-4 w-4 opacity-70 transition group-hover:translate-x-1" />
                  </div>
                  <div>
                    <p className="font-editorial text-3xl leading-none tracking-[-0.04em]">
                      {label}
                    </p>
                    <p
                      className={`mt-3 max-w-sm text-sm leading-7 ${
                        tone === 'dark' || tone === 'image' ? 'text-white/75' : 'text-ink-500'
                      }`}
                    >
                      {body}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </SurfaceCard>
      </div>
    </div>
  )
}

function HeroFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.2rem] border border-white/15 bg-white/10 p-3 backdrop-blur">
      <p className="text-[0.65rem] uppercase tracking-[0.2em] text-white/65">{label}</p>
      <p className="mt-2 text-sm font-medium text-white">{value}</p>
    </div>
  )
}

function ProgressStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm text-ink-700">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-1.5 rounded-full bg-sand-100">
        <div
          className="h-1.5 rounded-full bg-gradient-to-r from-accent-600 to-accent-500"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1rem] bg-sand-25 px-3 py-3">
      <p className="text-[0.65rem] uppercase tracking-[0.2em] text-ink-500">{label}</p>
      <p className="mt-2 font-medium text-ink-900">{value}</p>
    </div>
  )
}

function KnowledgeColumn({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="rounded-[1.5rem] border border-sand-200/80 bg-sand-25 p-4">
      <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
        {label}
      </p>
      <div className="mt-4 space-y-3 text-sm leading-6 text-ink-700">
        {items.length > 0 ? (
          items.map((item) => <p key={item}>{item}</p>)
        ) : (
          <p className="text-ink-500">This column fills in as ReFrame learns more.</p>
        )}
      </div>
    </div>
  )
}
