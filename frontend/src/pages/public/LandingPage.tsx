import { ArrowRight, Check, ClipboardList, Compass, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { SurfaceCard } from '../../components/Cards'
import { SectionHeader } from '../../components/SectionHeader'

const featureCards = [
  {
    title: 'AI Design Studio',
    body: 'Upload a real room, discuss the vision with AI, confirm the requirements, and generate versions you can refine.',
  },
  {
    title: 'Space-aware planning',
    body: 'Dimensions are used in Python heuristics so ReFrame can warn when layouts feel too tight.',
  },
  {
    title: 'Contractor-ready handoff',
    body: 'Turn approved room designs into practical execution briefs you can share with local professionals.',
  },
]

export function LandingPage() {
  return (
    <div className="pb-20">
      <section className="mx-auto grid max-w-7xl gap-10 px-6 pb-20 pt-10 lg:grid-cols-[1.1fr_0.9fr] lg:px-10 lg:pt-16">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white px-4 py-2 text-sm text-ink-500">
            <Sparkles className="h-4 w-4 text-accent-600" />
            AI-powered interior design and home planning
          </div>
          <div className="space-y-5">
            <h1 className="max-w-3xl text-5xl font-semibold tracking-tight text-ink-900 sm:text-6xl">
              Redesign your space. Reimagine your life.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-ink-500">
              ReFrame understands your room, design intent, dimensions, budget, and
              whole-home style so every design feels connected to a real project.
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-full bg-ink-900 px-6 py-3 text-sm font-medium text-white"
            >
              Get Started Free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#how-it-works"
              className="rounded-full border border-sand-200 bg-white px-6 py-3 text-sm font-medium text-ink-700"
            >
              See How It Works
            </a>
          </div>
          <div className="flex flex-wrap gap-6 text-sm text-ink-500">
            <span className="inline-flex items-center gap-2">
              <Check className="h-4 w-4 text-accent-600" />
              AI Interior Designer
            </span>
            <span className="inline-flex items-center gap-2">
              <Check className="h-4 w-4 text-accent-600" />
              Space Planner
            </span>
            <span className="inline-flex items-center gap-2">
              <Check className="h-4 w-4 text-accent-600" />
              Contractor Briefs
            </span>
          </div>
        </div>

        <SurfaceCard className="grid gap-4 bg-[linear-gradient(135deg,rgba(248,244,238,0.95),rgba(255,255,255,0.85))]">
          <div className="rounded-[24px] bg-white p-5">
            <p className="text-sm text-ink-500">Design Studio Preview</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[20px] bg-sand-100 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Original</p>
                <div className="mt-3 h-48 rounded-[18px] bg-[linear-gradient(180deg,#dcc7af,#f5eee4)]" />
              </div>
              <div className="rounded-[20px] bg-sand-100 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-ink-500">AI Design</p>
                <div className="mt-3 h-48 rounded-[18px] bg-[linear-gradient(180deg,#c7a785,#efe7db)]" />
              </div>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {featureCards.map((feature) => (
              <div key={feature.title} className="rounded-[24px] bg-white p-5">
                <p className="font-medium text-ink-900">{feature.title}</p>
                <p className="mt-2 text-sm leading-6 text-ink-500">{feature.body}</p>
              </div>
            ))}
          </div>
        </SurfaceCard>
      </section>

      <section id="how-it-works" className="mx-auto max-w-7xl px-6 py-20 lg:px-10">
        <SectionHeader
          eyebrow="How It Works"
          title="A full design workflow, not a one-shot image prompt"
          description="ReFrame turns a room photograph into a guided design process with memory, validation, and execution handoff."
        />
        <div className="mt-10 grid gap-6 lg:grid-cols-4">
          {[
            ['Upload your space', 'Room photo, type, and dimensions start the project.'],
            ['Discuss with AI', 'The assistant extracts style, budget, keep/remove/add, and avoid rules.'],
            ['Approve the plan', 'Users verify the requirement card before generation.'],
            ['Finalize and share', 'Save versions, score the design, and generate a contractor brief.'],
          ].map(([title, body]) => (
            <SurfaceCard key={title}>
              <p className="font-medium text-ink-900">{title}</p>
              <p className="mt-3 text-sm leading-6 text-ink-500">{body}</p>
            </SurfaceCard>
          ))}
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
        <div className="grid gap-6 lg:grid-cols-3">
          {[
            {
              icon: Sparkles,
              title: 'AI Design Studio',
              copy: 'The most important workflow: upload, chat, confirm, generate, iterate.',
            },
            {
              icon: Compass,
              title: 'Whole House Consistency',
              copy: 'ReFrame remembers materials, colours, lighting, and style signatures across rooms.',
            },
            {
              icon: ClipboardList,
              title: 'Execution-Ready Briefs',
              copy: 'Approved room concepts can be handed to professionals without repeating the full story.',
            },
          ].map(({ icon: Icon, title, copy }) => (
            <SurfaceCard key={title}>
              <Icon className="h-6 w-6 text-accent-600" />
              <p className="mt-5 text-xl font-semibold text-ink-900">{title}</p>
              <p className="mt-3 text-sm leading-6 text-ink-500">{copy}</p>
            </SurfaceCard>
          ))}
        </div>
      </section>

      <section id="pages" className="mx-auto max-w-7xl px-6 py-20 lg:px-10">
        <SectionHeader
          eyebrow="Build Scope"
          title="Page structure locked for implementation"
          description="The public site stays light while the logged-in app focuses on design creation, project continuity, and practical handoff."
        />
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            'Dashboard',
            'AI Design Studio',
            'My Home',
            'Inspiration Board',
            'Design Score',
            'Contractor Briefs',
            'Professionals',
            'Profile',
          ].map((label) => (
            <div
              key={label}
              className="rounded-[24px] border border-sand-200 bg-white px-5 py-4 text-sm font-medium text-ink-700"
            >
              {label}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
