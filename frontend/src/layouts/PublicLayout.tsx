import { ArrowRight } from 'lucide-react'
import { Link, Outlet } from 'react-router-dom'
import { publicNav } from '../data/mockData'

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
        <Link to="/" className="flex items-center gap-4 text-ink-900">
          <img
            src="/reframe-logo.png"
            alt="ReFrame"
            className="h-12 w-12 rounded-[1rem] object-cover ring-1 ring-sand-200"
          />
          <div>
            <p className="font-editorial text-3xl tracking-[-0.04em]">ReFrame</p>
            <p className="text-[0.65rem] uppercase tracking-[0.26em] text-ink-500">
              AI interior design
            </p>
          </div>
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          {publicNav.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-ink-500 transition hover:text-ink-900"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm font-medium text-ink-700">
            Login
          </Link>
          <Link
            to="/signup"
            className="inline-flex items-center gap-2 rounded-full bg-ink-900 px-5 py-3 text-sm font-medium text-white"
          >
            Get Started
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>
      <Outlet />
    </div>
  )
}
