'use client'

import { FormEvent, useState } from 'react'
import { authClient } from '@/lib/auth-client'
import { ensureWorkspace } from '@/app/actions/workspace'

export default function SignUpPage() {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError('')
    const data = new FormData(event.currentTarget)
    const result = await authClient.signUp.email({ name: String(data.get('name')), email: String(data.get('email')), password: String(data.get('password')) })
    if (result.error) setError('Unable to create your workspace account. Please check your details.')
    else { try { await ensureWorkspace(); window.location.href = '/' } catch { setError('Account created, but workspace setup needs another attempt.') } }
    setLoading(false)
  }
  return <main className="auth-page"><section className="auth-card"><div className="auth-mark">A</div><p className="eyebrow">AURA WORKSPACE</p><h1>Create account</h1><p className="auth-copy">Set up your secure evidence and loan operations workspace.</p><form onSubmit={submit}><label>Full name<input name="name" autoComplete="name" required /></label><label>Work email<input name="email" type="email" autoComplete="email" required /></label><label>Password<input name="password" type="password" minLength={8} autoComplete="new-password" required /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={loading}>{loading ? 'Creating account…' : 'Create account'}</button></form><p className="auth-copy auth-switch">Already have an account? <a href="/sign-in">Sign in</a></p></section></main>
}
