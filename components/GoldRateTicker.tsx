'use client'

import { useEffect, useState, useCallback } from 'react'
import { TrendingUp, TrendingDown, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { api, AllGoldRates } from '@/lib/api'

const REFRESH_INTERVAL_MS = 10 * 60 * 1000 // 10 minutes (respects free API cache)

function fmt(inr: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(inr)
}

interface KaratTile {
  karat: string
  label: string
  fineness: string
}

const KARATS: KaratTile[] = [
  { karat: '24K', label: '24 Karat', fineness: '999' },
  { karat: '22K', label: '22 Karat', fineness: '916' },
  { karat: '18K', label: '18 Karat', fineness: '750' },
]

export function GoldRateTicker() {
  const [rates, setRates] = useState<AllGoldRates | null>(null)
  const [prevRates, setPrevRates] = useState<AllGoldRates | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await api.getLiveGoldRates()
      setPrevRates(r => r)
      setRates(data)
      setLastFetch(new Date())
    } catch {
      // silently keep stale data
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, REFRESH_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refresh])

  if (loading) {
    return (
      <div className="gold-ticker loading">
        <RefreshCw size={14} className="spin" />
        <span>Loading live gold rates…</span>
      </div>
    )
  }

  if (!rates) return null

  return (
    <div className="gold-ticker-wrap">
      <div className="gold-ticker-header">
        <div className="gold-ticker-title">
          <span className="section-kicker">LIVE GOLD RATES · INDIA</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            {rates.is_live
              ? <><Wifi size={12} style={{ color: '#2aaf7f' }} /><span style={{ fontSize: '10px', color: '#2aaf7f' }}>Live · {rates.source}</span></>
              : <><WifiOff size={12} style={{ color: '#e8a527' }} /><span style={{ fontSize: '10px', color: '#e8a527' }}>Static fallback</span></>
            }
          </div>
        </div>
        <button
          className="icon-button"
          onClick={refresh}
          title="Refresh gold rates"
          style={{ fontSize: '10px', gap: '4px' }}
        >
          <RefreshCw size={13} />
        </button>
      </div>

      <div className="gold-ticker-grid">
        {KARATS.map(({ karat, label, fineness }) => {
          const rateData = rates.rates[karat]
          const prevRate = prevRates?.rates[karat]
          const inrPerGram = rateData?.inr_per_gram ?? 0
          const prevInr = prevRate?.inr_per_gram ?? inrPerGram
          const delta = inrPerGram - prevInr
          const up = delta > 0
          const down = delta < 0

          return (
            <div key={karat} className="gold-rate-tile">
              <div className="gold-rate-karat">
                <span className="karat-badge">{karat}</span>
                <small>{label} · {fineness} purity</small>
              </div>
              <div className="gold-rate-value">
                <strong>{fmt(inrPerGram)}<small>/g</small></strong>
                {delta !== 0 && (
                  <span className={`rate-delta ${up ? 'up' : 'down'}`}>
                    {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                    {up ? '+' : ''}{fmt(Math.abs(delta))}
                  </span>
                )}
              </div>
              <div className="gold-rate-meta">
                ₹{(inrPerGram / 10).toFixed(0)}/100mg · ₹{(inrPerGram * 10).toFixed(0)}/10g
              </div>
            </div>
          )
        })}
      </div>

      {lastFetch && (
        <div className="gold-ticker-footer">
          Last updated: {lastFetch.toLocaleTimeString('en-IN')} · v{rates.rate_version} · Cache age: {rates.cache_age_seconds}s
        </div>
      )}
    </div>
  )
}
