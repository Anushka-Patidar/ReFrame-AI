import { useEffect, useState } from 'react'
import { ArrowRight, BrainCircuit, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { EditorialImage } from '../../components/EditorialImage'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'
import { useAuth } from '../../context/AuthContext'
import { editorialImages } from '../../data/interiorImages'
import { api } from '../../lib/api'
import type { ChatMessage, DesignRequirements, Room } from '../../types/api'

export function DesignChatPage() {
  const { roomId = '' } = useParams()
  const { token } = useAuth()
  const [room, setRoom] = useState<Room | null>(null)
  const [requirements, setRequirements] = useState<DesignRequirements | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'I can help redesign your room. Tell me the style, budget, what to keep, and what to remove.',
    },
  ])
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [isSending, setIsSending] = useState(false)

  useEffect(() => {
    if (!token) return
    void Promise.all([
      api.getRoom(token, roomId),
      api.getRequirements(token, roomId),
      api.getConversation(token, roomId),
    ])
      .then(([nextRoom, nextRequirements, conversation]) => {
        setRoom(nextRoom)
        setRequirements(nextRequirements)
        if (conversation.length > 0) {
          setMessages(conversation)
        }
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load the design conversation.',
        ),
      )
  }, [roomId, token])

  async function sendMessage() {
    if (!token || !draft.trim()) return

    setError('')
    setIsSending(true)

    try {
      const response = await api.sendChat(token, roomId, {
        role: 'user',
        content: draft.trim(),
      })
      setMessages((current) => [...current, ...response])
      setDraft('')
      const refreshed = await api.getRequirements(token, roomId)
      setRequirements(refreshed)
    } catch (sendError) {
      setError(
        sendError instanceof Error ? sendError.message : 'Unable to send your message.',
      )
    } finally {
      setIsSending(false)
    }
  }

  const liveTags = [
    requirements?.style,
    ...(requirements?.keep.slice(0, 1).map((item) => `Keep ${item}`) ?? []),
    ...(requirements?.remove.slice(0, 1).map((item) => `Remove ${item}`) ?? []),
    ...(requirements?.add.slice(0, 1).map((item) => `Add ${item}`) ?? []),
    requirements?.budget ? `₹${requirements.budget.toLocaleString('en-IN')}` : null,
  ].filter(Boolean) as string[]

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="AI Design Studio"
        title="Discuss the room with AI before anything is generated."
        description="This is where ReFrame becomes personal: what to keep, what to change, what to remove, and how the room should feel."
      />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <SurfaceCard className="space-y-6 overflow-hidden">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`max-w-2xl rounded-[1.7rem] px-5 py-4 ${
                    message.role === 'assistant'
                      ? 'bg-sand-25 text-ink-700'
                      : 'ml-auto bg-ink-950 text-white'
                  }`}
                >
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em]">
                    {message.role === 'assistant' ? 'AI Interior Designer' : 'You'}
                  </p>
                  <p className="mt-3 text-sm leading-7">{message.content}</p>
                </div>
              ))}
            </div>

            <EditorialImage
              src={room?.original_image_url || editorialImages.bedroom}
              alt="Conversation mood"
              overlay
              className="min-h-[320px] rounded-[1.8rem]"
            >
              <div className="flex h-full flex-col justify-between p-5 text-white">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/10 backdrop-blur">
                    <BrainCircuit className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-white/70">
                      ReFrame memory
                    </p>
                    <p className="mt-2 text-sm text-white/90">
                      Keep / Change / Remove signals are being structured live.
                    </p>
                  </div>
                </div>
                <div className="grid gap-3">
                  {(liveTags.length
                    ? liveTags
                    : ['Warm colours', 'Keep wardrobe', 'Remove curtains', 'Budget-aware']
                  ).map((tag) => (
                    <span
                      key={tag}
                      className="w-fit rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.18em] backdrop-blur"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </EditorialImage>
          </div>

          <div className="rounded-[1.8rem] border border-sand-200 bg-white/75 p-5">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              rows={4}
              placeholder="I want Japandi style, keep the wardrobe, remove the curtains, add warm lighting, budget 90000."
              className="w-full resize-none rounded-[1.2rem] border border-sand-200 bg-sand-25 px-4 py-4 text-sm leading-7 outline-none"
            />
            {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-ink-500">
                The richer your notes, the better ReFrame can structure the plan.
              </p>
              <button
                type="button"
                onClick={sendMessage}
                disabled={isSending}
                className="inline-flex rounded-full bg-ink-950 px-5 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5 disabled:opacity-60"
              >
                {isSending ? 'Sending...' : 'Send Message'}
              </button>
            </div>
          </div>
        </SurfaceCard>

        <div className="grid gap-6">
          <SurfaceCard className="space-y-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full border border-sand-200 bg-sand-25 text-accent-600">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
                  Design plan in progress
                </p>
                <p className="mt-2 font-editorial text-3xl tracking-[-0.04em] text-ink-950">
                  ReFrame is distilling the brief.
                </p>
              </div>
            </div>
            <div className="space-y-4 text-sm leading-7 text-ink-500">
              <p>Style: {requirements?.style ?? 'Waiting for direction'}</p>
              <p>
                Keep:{' '}
                {requirements?.keep.length ? requirements.keep.join(', ') : 'Not set yet'}
              </p>
              <p>
                Add: {requirements?.add.length ? requirements.add.join(', ') : 'Not set yet'}
              </p>
            </div>
            <Link
              to={`/app/design-studio/${roomId}/plan`}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink-950 px-5 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5"
            >
              Review Design Plan
              <ArrowRight className="h-4 w-4" />
            </Link>
          </SurfaceCard>

          <SurfaceCard className="space-y-4">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-accent-600">
              Conversation prompts
            </p>
            <div className="grid gap-3">
              {[
                'Keep the wardrobe and bed, remove the curtains.',
                'Make it Japandi with warm beige and soft lighting.',
                'Add a reading chair, budget around 90000.',
              ].map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setDraft(prompt)}
                  className="rounded-[1.25rem] border border-sand-200 bg-sand-25 px-4 py-3 text-left text-sm text-ink-700 transition hover:border-accent-500"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </SurfaceCard>
        </div>
      </div>
    </div>
  )
}
