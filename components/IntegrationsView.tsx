'use client'

import { useState } from 'react'
import {
  ShieldCheck, AlertTriangle, CheckCircle2, RefreshCw, SlidersHorizontal,
  Zap, Lock, Activity, ArrowRight, ExternalLink
} from 'lucide-react'
import { api, AdapterStatus } from '@/lib/api'

interface IntegrationsViewProps {
  adapters: AdapterStatus[]
  onRefresh: () => void
  setToast: (msg: string) => void
  hasApiSession: boolean
}

export function IntegrationsView({ adapters, onRefresh, setToast, hasApiSession }: IntegrationsViewProps) {
  const [testingName, setTestingName] = useState<string | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('All')

  const categories = ['All', ...Array.from(new Set(adapters.map(a => a.category)))]
  const filtered = categoryFilter === 'All'
    ? adapters
    : adapters.filter(a => a.category === categoryFilter)

  async function handleModeChange(adapterName: string, newMode: string) {
    try {
      await api.updateIntegrationMode(adapterName, newMode)
      setToast(`${adapterName} switched to ${newMode} mode`)
      onRefresh()
    } catch (err: any) {
      setToast(err.message || 'Failed to switch mode')
    }
  }

  async function handleFailureSim(adapterName: string, scenario: string) {
    try {
      await api.simulateIntegrationFailure(adapterName, scenario === 'clear' ? undefined : scenario)
      setToast(`${adapterName}: ${scenario === 'clear' ? 'Cleared failure simulation' : `Injected ${scenario}`}`)
      onRefresh()
    } catch (err: any) {
      setToast(err.message || 'Failed to set failure scenario')
    }
  }

  async function handleTestConnection(adapterName: string) {
    setTestingName(adapterName)
    try {
      const res = await api.testIntegrationConnection(adapterName)
      if (res.status === 'SIMULATED') {
        setToast(`${adapterName}: ${res.message}`)
      } else if (res.success) {
        setToast(`✓ ${adapterName}: Connected in ${res.latency_ms}ms`)
      } else {
        setToast(`⚠ ${adapterName}: ${res.error || 'Connection degraded'}`)
      }
      onRefresh()
    } catch (err: any) {
      setToast(err.message || 'Connection test failed')
    } finally {
      setTestingName(null)
    }
  }

  return (
    <section className="subpage">
      <div className="subpage-head">
        <div>
          <h2>Integrations & Environment Settings</h2>
          <p>Configure integration adapters (Mock, Sandbox, Production), verify webhooks, and inject resilience tests.</p>
        </div>
        <button className="secondary-button" onClick={onRefresh} disabled={!hasApiSession}>
          <RefreshCw size={14} /> Refresh Adapter Status
        </button>
      </div>

      {/* SAFETY CONTROLS BANNER */}
      <div className="safeguards-banner">
        <ShieldCheck size={28} className="text-blue-600" />
        <div>
          <h4>Three-Tier Safe Integration Boundary (Mock / Sandbox / Production)</h4>
          <p>
            In this build, MOCK and SANDBOX modes use local simulators only; no provider connection is attempted.
            Production provider clients are not implemented and remain unavailable. A green or simulated result
            is not evidence of a live provider connection, payment settlement, or device-authenticated assay.
          </p>
        </div>
      </div>

      {/* SUMMARY STATS */}
      <div className="team-stats">
        <div>
          <Zap size={19} />
          <strong>{adapters.length || 10}</strong>
          <span>Configured adapters</span>
        </div>
        <div>
          <ShieldCheck size={19} />
          <strong>3 Modes</strong>
          <span>MOCK, SANDBOX, PROD</span>
        </div>
        <div>
          <Lock size={19} />
          <strong>HMAC-SHA256</strong>
          <span>Local webhook signature simulation</span>
        </div>
      </div>

      {/* FILTER TABS */}
      <div className="tab-row" style={{ marginTop: '10px' }}>
        {categories.map(cat => (
          <button
            key={cat}
            className={`tab-btn ${categoryFilter === cat ? 'active' : ''}`}
            onClick={() => setCategoryFilter(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* ADAPTER CARDS GRID */}
      <div className="adapter-grid">
        {filtered.map(adapter => {
          const healthClass = adapter.health === 'HEALTHY'
            ? 'healthy'
            : adapter.health === 'DEGRADED' || adapter.health === 'SIMULATED'
            ? 'degraded'
            : 'unavailable'

          return (
            <div className={`adapter-card ${healthClass}`} key={adapter.name}>
              <div className="adapter-head">
                <div>
                  <h3>{adapter.name}</h3>
                  <p>{adapter.description}</p>
                </div>
              </div>

              <div className="adapter-meta">
                <span className={`mode-pill ${adapter.mode}`}>{adapter.mode} MODE</span>
                <span className={`status ${adapter.health === 'HEALTHY' ? 'green' : adapter.health === 'DEGRADED' || adapter.health === 'SIMULATED' ? 'amber' : 'red'}`}>
                  <span /> {adapter.health}
                </span>
                <span className="latency-pill">{adapter.latency_ms || 12}ms</span>
                {adapter.simulated_failure && (
                  <span style={{ fontSize: '9px', background: '#fee2e2', color: '#991b1b', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                    SIM: {adapter.simulated_failure}
                  </span>
                )}
              </div>

              {adapter.last_error && (
                <div style={{ fontSize: '10px', color: '#991b1b', background: '#fef2f2', padding: '6px 8px', borderRadius: '4px' }}>
                  <strong>Last Error:</strong> {adapter.last_error}
                </div>
              )}

              {/* SERVER CONFIG MASKED KEYS */}
              <div className="adapter-configs">
                <strong>Server Configuration Safeguards:</strong>
                {adapter.required_configs && adapter.required_configs.length > 0 ? (
                  adapter.required_configs.map(cfg => (
                    <div className="config-item" key={cfg.key}>
                      <span>{cfg.key}</span>
                      <span className={`config-status ${cfg.configured ? 'configured' : 'missing'}`}>
                        {cfg.configured ? 'CONFIGURED' : 'UNSET'}
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#8898aa', fontSize: '9px' }}>Deterministic local simulator (No external secrets needed)</div>
                )}
              </div>

              {/* ACTION CONTROLS */}
              <div className="adapter-actions">
                <div style={{ display: 'grid', gap: '3px', flex: 1 }}>
                  <label style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>RUNTIME MODE</label>
                  <select
                    value={adapter.mode}
                    onChange={e => handleModeChange(adapter.name, e.target.value)}
                    disabled={!hasApiSession}
                  >
                    <option value="MOCK">MOCK (Local Simulator)</option>
                    <option value="SANDBOX">SANDBOX (Local Simulator)</option>
                    <option value="PRODUCTION">PRODUCTION (Live Rail)</option>
                  </select>
                </div>

                <div style={{ display: 'grid', gap: '3px', flex: 1 }}>
                  <label style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>INJECT FAILURE</label>
                  <select
                    value={adapter.simulated_failure || 'clear'}
                    onChange={e => handleFailureSim(adapter.name, e.target.value)}
                    disabled={!hasApiSession}
                  >
                    <option value="clear">None (Normal)</option>
                    <option value="timeout">Timeout (30s delay)</option>
                    <option value="invalid_signature">Invalid HMAC Signature</option>
                    <option value="duplicate">Duplicate Callback</option>
                    <option value="mismatch">Amount Mismatch</option>
                    <option value="upstream_500">Upstream 502/503</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                  <button
                    onClick={() => handleTestConnection(adapter.name)}
                    disabled={!hasApiSession || testingName === adapter.name}
                  >
                    {testingName === adapter.name ? 'Pinging...' : 'Test Ping'}
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
