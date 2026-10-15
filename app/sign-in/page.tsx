'use client'

import { FormEvent, useState } from 'react'
import { authClient } from '@/lib/auth-client'

export default function SignInPage() {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    const data = new FormData(event.currentTarget)
    const result = await authClient.signIn.email({ email: String(data.get('email')), password: String(data.get('password')) })
    if (result.error) setError('Unable to sign in. Check your email and password.')
    else window.location.href = '/'
    setLoading(false)
  }
  return <main className="auth-page"><section className="auth-card"><div className="auth-mark">A</div><p className="eyebrow">AURA WORKSPACE</p><h1>Welcome back</h1><p className="auth-copy">Sign in to manage evidence, applications, and decisions.</p><form onSubmit={submit}><label>Email<input name="email" type="email" autoComplete="email" required /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button></form><p className="auth-copy auth-switch">New to AURA? <a href="/sign-up">Create an account</a></p></section></main>
}
