import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { AuthShell } from './AuthShell'

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState({
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await login(form)
      navigate('/app/dashboard')
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : 'Unable to log in right now.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to continue your interior design project."
      footer={
        <>
          Don&apos;t have an account?{' '}
          <Link to="/signup" className="font-medium text-accent-600">
            Sign up
          </Link>
        </>
      }
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        {[
          ['Email address', 'name@example.com', 'email', 'email'],
          ['Password', 'Enter your password', 'password', 'password'],
        ].map(([label, placeholder, type, name]) => (
          <label key={label} className="block space-y-2">
            <span className="text-sm font-medium text-ink-700">{label}</span>
            <input
              type={type}
              placeholder={placeholder}
              value={form[name as keyof typeof form]}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  [name]: event.target.value,
                }))
              }
              className="w-full rounded-2xl border border-sand-200 bg-surface px-4 py-3 text-sm outline-none transition focus:border-accent-500"
            />
          </label>
        ))}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <div className="flex justify-end">
          <button type="button" className="text-sm font-medium text-ink-500">
            Forgot password?
          </button>
        </div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex w-full justify-center rounded-2xl bg-ink-900 px-4 py-3 text-sm font-medium text-white disabled:opacity-60"
        >
          {isSubmitting ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </AuthShell>
  )
}
