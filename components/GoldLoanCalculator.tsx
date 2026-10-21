'use client'

import { useState, useCallback } from 'react'
import { Calculator, ChevronDown, Info, TrendingUp } from 'lucide-react'
import { api, ValuationResponse } from '@/lib/api'

const PURITY_OPTIONS = [
  { label: '24 Karat (999)', value: 9990, karat: '24K' },
  { label: '22 Karat (916)', value: 9160, karat: '22K' },
  { label: '18 Karat (750)', value: 7500, karat: '18K' },
]

const LTV_OPTIONS = [
  { label: '85% LTV (≤ ₹2.5 L)', value: 85 },
  { label: '80% LTV (₹2.5–5 L)', value: 80 },
  { label: '75% LTV (> ₹5 L)', value: 75 },
]

function fmtINR(paise: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(paise / 100)
}

function fmtGrams(mg: number): string {
  return (mg / 1000).toFixed(3) + ' g'
}

export function GoldLoanCalculator({ setToast }: { setToast?: (msg: string) => void }) {
  const [weightGrams, setWeightGrams] = useState('25')
  const [stoneDedGrams, setStoneDedGrams] = useState('0')
  const [purityBps, setPurityBps] = useState(9160)
  const [ltvPct, setLtvPct] = useState(80)
  const [creditLimitLakh, setCreditLimitLakh] = useState('10')
  const [result, setResult] = useState<ValuationResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const calculate = useCallback(async () => {
    const grams = parseFloat(weightGrams)
    const stoneDed = parseFloat(stoneDedGrams) || 0
    if (!grams || grams <= 0) {
      setToast?.('Enter a valid gold weight')
      return
    }
    setLoading(true)
    try {
      const res = await api.calculateValuation({
        items: [{
          item_type: 'Gold Ornament',
          gross_weight_mg: Math.round(grams * 1000),
          stone_deduction_mg: Math.round(stoneDed * 1000),
          purity_bps: purityBps,
        }],
        ltv_scheme_pct: ltvPct,
        credit_limit_paise: Math.round(parseFloat(creditLimitLakh) * 100000 * 100),
      })
      setResult(res)
    } catch (err: any) {
      setToast?.(err.message || 'Calculation failed')
    } finally {
      setLoading(false)
    }
  }, [weightGrams, stoneDedGrams, purityBps, ltvPct, creditLimitLakh, setToast])

  const summary = result?.summary
  const collateralLimit = result?.limits_comparison_paise.COLLATERAL_LTV_LIMIT

  return (
    <div className="calculator-wrap panel">
      <div className="panel-heading">
        <div>
          <span className="section-kicker">GOLD LOAN CALCULATOR</span>
          <h2>Estimate your eligible loan amount</h2>
          <p>Uses live gold market rates · All calculations are indicative only</p>
        </div>
        <Calculator size={22} style={{ color: '#c9a227' }} />
      </div>

      <div className="calc-form">
        <div className="calc-row">
          <label>
            Gross weight (grams)
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={weightGrams}
              onChange={e => setWeightGrams(e.target.value)}
              placeholder="e.g. 25.0"
            />
          </label>
          <label>
            Stone / impurity deduction (grams)
            <input
              type="number"
              min="0"
              step="0.1"
              value={stoneDedGrams}
              onChange={e => setStoneDedGrams(e.target.value)}
              placeholder="0.0"
            />
          </label>
        </div>

        <div className="calc-row">
          <label>
            Gold purity
            <select value={purityBps} onChange={e => setPurityBps(Number(e.target.value))}>
              {PURITY_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label>
            LTV scheme
            <select value={ltvPct} onChange={e => setLtvPct(Number(e.target.value))}>
              {LTV_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="calc-row">
          <label>
            Credit limit (₹ lakhs)
            <input
              type="number"
              min="1"
              step="1"
              value={creditLimitLakh}
              onChange={e => setCreditLimitLakh(e.target.value)}
              placeholder="10"
            />
          </label>
        </div>

        <button
          className="primary-button"
          onClick={calculate}
          disabled={loading}
          style={{ marginTop: '8px' }}
        >
          {loading ? 'Calculating…' : <><Calculator size={15} /> Calculate eligible amount</>}
        </button>
      </div>

      {summary && (
        <div className="calc-result">
          <div className="calc-eligible">
            <span className="eyebrow">ELIGIBLE LOAN AMOUNT</span>
            <strong className="eligible-amount">{fmtINR(summary.eligible_loan_amount_paise)}</strong>
            <small>Binding constraint: <em>{summary.binding_constraint?.replace('_', ' ')}</em></small>
          </div>

          <div className="calc-breakdown">
            <div className="breakdown-row">
              <span><TrendingUp size={12} /> Net gold weight</span>
              <strong>{fmtGrams(summary.total_net_weight_mg)}</strong>
            </div>
            <div className="breakdown-row">
              <span><TrendingUp size={12} /> Fine weight ({(purityBps / 100).toFixed(1)}%)</span>
              <strong>{fmtGrams(summary.total_fine_weight_mg)}</strong>
            </div>
            <div className="breakdown-row">
              <span>Gold market value</span>
              <strong>{fmtINR(summary.total_gold_valuation_paise)}</strong>
            </div>
            <div className="breakdown-row">
              <span>LTV applied</span>
              <strong>{summary.applied_ltv_pct}%</strong>
            </div>
            <div className="breakdown-row highlight">
              <span>Collateral limit ({summary.applied_ltv_pct}% × value)</span>
              <strong>{fmtINR(collateralLimit ?? summary.eligible_loan_amount_paise)}</strong>
            </div>
            <div className="breakdown-row rate-row">
              <span><Info size={11} /> Rate version</span>
              <small>{summary.rate_version}</small>
            </div>
          </div>

          <div className="calc-disclaimer">
            <Info size={11} />
            Indicative calculation only. Actual eligibility is subject to KYC, assay results, credit assessment, and lender policies. Rates from live market feed.
          </div>
        </div>
      )}
    </div>
  )
}
