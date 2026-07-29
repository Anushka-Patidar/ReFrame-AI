import { useState } from 'react'
import {
  Compass,
  FolderKanban,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  UserCircle,
  Users,
  X,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { appNav } from '../data/mockData'

const icons = {
  Dashboard: LayoutDashboard,
  'AI Design Studio': Sparkles,
  'My Home': Compass,
  Inspiration: Lightbulb,
  'Contractor Briefs': FolderKanban,
  Professionals: Users,
  Profile: UserCircle,
  Settings,
}

export function AppShell() {
  const { user, logout } = useAuth()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-sand-50 text-ink-900 lg:grid lg:grid-cols-[320px_1fr]">
      <button
        type="button"
        onClick={() => setIsSidebarOpen(true)}
        className="fixed left-5 top-5 z-40 inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white/90 px-4 py-3 text-sm font-medium text-ink-900 shadow-[var(--shadow-float)] lg:hidden"
      >
        <Menu className="h-4 w-4" />
        Menu
      </button>

      {isSidebarOpen ? (
        <button
          type="button"
          aria-label="Close sidebar backdrop"
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[88vw] max-w-[320px] overflow-y-auto border-r border-white/10 bg-[#1b1815] px-6 py-6 text-white transition duration-300 lg:sticky lg:top-0 lg:h-screen lg:w-auto lg:max-w-none ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        <div className="flex items-start justify-between">
          <div className="space-y-5">
            <div className="flex items-center gap-4">
              <img
                src="/reframe-logo.png"
                alt="ReFrame"
                className="h-14 w-14 rounded-[1.2rem] object-cover ring-1 ring-white/10"
              />
              <div>
                <p className="font-editorial text-3xl tracking-[-0.04em] text-white">
                  ReFrame
                </p>
                <p className="mt-1 text-[0.7rem] uppercase tracking-[0.3em] text-white/45">
                  Interior intelligence
                </p>
              </div>
            </div>
            <p className="max-w-xs text-sm leading-7 text-white/60">
              AI that understands your home, remembers your taste, and guides each
              room toward a shared design language.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="my-8 h-px bg-white/10" />

        <nav className="grid gap-1.5">
          {appNav.map((item) => {
            const Icon = icons[item.label as keyof typeof icons]
            return (
              <NavLink key={item.href} to={item.href} onClick={() => setIsSidebarOpen(false)}>
                {({ isActive }) => (
                  <div
                    className={`group relative overflow-hidden rounded-[1.35rem] border px-4 py-4 transition ${
                      isActive
                        ? 'border-white/10 bg-[linear-gradient(90deg,rgba(255,255,255,0.12),rgba(255,255,255,0.04))] text-white'
                        : 'border-transparent bg-transparent text-white/60 hover:border-white/8 hover:bg-white/[0.04] hover:text-white'
                    }`}
                  >
                    <div
                      className={`absolute inset-y-4 left-0 w-px bg-accent-500 transition ${
                        isActive ? 'opacity-100' : 'opacity-0'
                      }`}
                    />
                    <div className="flex items-center gap-3">
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.04]">
                        <Icon className="h-4 w-4" />
                      </span>
                      <div>
                        <p className="text-sm font-medium">{item.label}</p>
                        <p className="text-xs text-white/45">{item.description}</p>
                      </div>
                    </div>
                  </div>
                )}
              </NavLink>
            )
          })}
        </nav>

        <div className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-4 backdrop-blur">
          <p className="text-[0.7rem] uppercase tracking-[0.3em] text-white/40">
            Designer profile
          </p>
          <div className="mt-4 flex items-start gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-lg font-semibold text-ink-950">
              {user?.name?.[0] ?? 'R'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-white">{user?.name}</p>
              <p className="mt-1 truncate text-sm text-white/45">{user?.email}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-white/80 transition hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      </aside>

      <main className="px-4 pb-10 pt-20 sm:px-8 lg:px-10 lg:pt-8">
        <div className="mx-auto max-w-[1280px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
