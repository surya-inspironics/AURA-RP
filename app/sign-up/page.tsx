'use client'

import { FormEvent, useState } from 'react'
import { api } from '@/lib/api'

export default function SignUpPage() {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    const data = new FormData(event.currentTarget)
    try {
      const session = await api.register({
        full_name: String(data.get('name')),
        email: String(data.get('email')),
        password: String(data.get('password')),
        organization_name: String(data.get('organization') || '')
      })
      api.storeSession(session)
      window.location.href = '/'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create your workspace account.')
    } finally {
      setLoading(false)
    }
  }
  return <main className="auth-page"><section className="auth-card"><div className="auth-mark">A</div><p className="eyebrow">AURUM WORKSPACE</p><h1>Create account</h1><p className="auth-copy">Set up your secure evidence and loan operations workspace.</p><form onSubmit={submit}><label>Full name<input name="name" autoComplete="name" required /></label><label>Work email<input name="email" type="email" autoComplete="email" required /></label><label>Organisation<input name="organization" autoComplete="organization" /></label><label>Password<input name="password" type="password" minLength={8} autoComplete="new-password" required /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={loading}>{loading ? 'Creating account…' : 'Create account'}</button></form><p className="auth-copy auth-switch">Already have an account? <a href="/sign-in">Sign in</a></p></section></main>
}
