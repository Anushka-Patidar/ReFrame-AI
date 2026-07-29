import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { AuthShell } from './AuthShell'

export function SignUpPage() {
  const navigate = useNavigate()
  const { signup } = useAuth()
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    city: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await signup({
        name: form.name,
        email: form.email,
        phone: form.phone,
        city: form.city,
        password: form.password,
      })
      navigate('/app/dashboard')
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : 'Unable to create account.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start your ReFrame project with the details needed to personalize your home."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-accent-600">
            Log in
          </Link>
        </>
      }
    >
      <form className="grid gap-4" onSubmit={handleSubmit}>
        {[
          ['Name', 'Anushka Patidar', 'text', 'name'],
          ['Email', 'anushka@example.com', 'email', 'email'],
          ['Phone number', '+91 98765 43210', 'tel', 'phone'],
          ['City', 'Indore', 'text', 'city'],
          ['Password', 'Create password', 'password', 'password'],
          ['Confirm password', 'Confirm password', 'password', 'confirmPassword'],
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
        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 inline-flex w-full justify-center rounded-2xl bg-ink-900 px-4 py-3 text-sm font-medium text-white disabled:opacity-60"
        >
          {isSubmitting ? 'Creating Account...' : 'Create Account'}
        </button>
      </form>
    </AuthShell>
  )
}
