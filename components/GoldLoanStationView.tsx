'use client'

import { useState } from 'react'
import {
  Zap, ShieldCheck, AlertTriangle, FileText,
  Activity, Scale, Coins, RefreshCw
} from 'lucide-react'
import { api, ValuationResponse } from '@/lib/api'

interface GoldLoanStationProps {
  setToast: (msg: string) => void
  hasApiSession: boolean
}

export function GoldLoanStationView({ setToast, hasApiSession }: GoldLoanStationProps) {
  // Device & Assay state
  const [deviceId, setDeviceId] = useState('DEV-XRF-001')
  const [itemType, setItemType] = useState('Gold Bangle')
  const [grossWeightGrams, setGrossWeightGrams] = useState(25.5)
  const [stoneDeductionGrams, setStoneDeductionGrams] = useState(1.5)
  const [purityBps, setPurityBps] = useState(9160) // 22K (91.6%)
  const [verifiedReading, setVerifiedReading] = useState<any>(null)
  const [assayLoading, setAssayLoading] = useState(false)

  // Valuation & Eligibility state
  const [ltvScheme, setLtvScheme] = useState(75)
  const [creditLimitInr, setCreditLimitInr] = useState(500000)
  const [valuationResult, setValuationResult] = useState<ValuationResponse | null>(null)
  const [calcLoading, setCalcLoading] = useState(false)

  // Customer KYC check state
  const [customerName, setCustomerName] = useState('')
  const [panNumber, setPanNumber] = useState('')
  const [aadhaarNumber, setAadhaarNumber] = useState('')
  const [aadhaarOtp, setAadhaarOtp] = useState('')
  const [simulatorConsent, setSimulatorConsent] = useState(false)
  const [kycResult, setKycResult] = useState<any>(null)
  const [kycLoading, setKycLoading] = useState(false)

  // 1. Capture Signed Device Reading
  async function handleCaptureReading() {
    setAssayLoading(true)
    try {
      const grossMg = Math.round(grossWeightGrams * 1000)
      const rawReading = await api.simulateDeviceReading(deviceId, grossMg, purityBps)
      const verified = await api.verifyDeviceReading(rawReading)
      setVerifiedReading(verified)
      setToast(`Simulated assay signature checked: ${verified.purity_karat}K (${verified.gross_weight_mg / 1000}g). Not an authenticated device reading.`)
    } catch (err: any) {
      setToast(err.message || 'Assay reading failed')
    } finally {
      setAssayLoading(false)
    }
  }

  // 2. Run Eligibility Engine
  async function handleCalculateEligibility() {
    setCalcLoading(true)
    try {
      const grossMg = Math.round(grossWeightGrams * 1000)
      const stoneMg = Math.round(stoneDeductionGrams * 1000)
      const result = await api.calculateValuation({
        items: [{
          item_type: itemType,
          gross_weight_mg: grossMg,
          stone_deduction_mg: stoneMg,
          purity_bps: purityBps
        }],
        ltv_scheme_pct: ltvScheme,
        credit_limit_paise: creditLimitInr * 100
      })
      setValuationResult(result)
      setToast(`Simulated valuation calculated: ₹${result.summary.eligible_loan_amount_inr.toLocaleString('en-IN')}; not a lending decision.`)
    } catch (err: any) {
      setToast(err.message || 'Valuation failed')
    } finally {
      setCalcLoading(false)
    }
  }

  // 3. KYC Verification
  async function handleVerifyKyc() {
    if (!hasApiSession) {
      setToast('Sign in to use protected gold-loan tools.')
      return
    }
    if (!customerName.trim() || !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(panNumber.trim().toUpperCase()) || !/^\d{12}$/.test(aadhaarNumber.trim()) || !/^\d{6}$/.test(aadhaarOtp.trim())) {
      setToast('Enter a name, valid synthetic PAN/Aadhaar formats, and the six-digit simulator OTP.')
      return
    }
    if (!simulatorConsent) {
      setToast('Confirm consent to run the local KYC simulator.')
      return
    }

    setKycLoading(true)
    try {
      const panRes = await api.verifyPan(panNumber, customerName)
      const aadhaarRes = await api.verifyAadhaar(aadhaarNumber, aadhaarOtp, simulatorConsent)
      setKycResult({ pan: panRes, aadhaar: aadhaarRes })
      setPanNumber('')
      setAadhaarNumber('')
      setAadhaarOtp('')
      setToast('Simulation complete only — identity was not verified by a provider.')
    } catch (err: any) {
      setToast(err.message || 'KYC verification failed')
    } finally {
      setKycLoading(false)
    }
  }

  const safeGrossWeightGrams = Number.isFinite(grossWeightGrams) ? Math.max(0, grossWeightGrams) : 0
  const safeStoneDeductionGrams = Number.isFinite(stoneDeductionGrams) ? Math.max(0, stoneDeductionGrams) : 0
  const netWeightGrams = Math.max(0, safeGrossWeightGrams - safeStoneDeductionGrams)
  const fineWeightGrams = valuationResult?.summary.total_fine_weight_g ?? netWeightGrams * purityBps / 10000
  const indicativeValue = valuationResult?.summary.total_gold_valuation_inr ?? null
  const indicativeFacility = valuationResult?.summary.eligible_loan_amount_inr ?? null
  const facilityShare = indicativeValue && indicativeFacility
    ? Math.min(100, indicativeFacility / indicativeValue * 100)
    : 0
  const weightSegments = [
    { label: 'Stone / non-gold deduction', value: Math.min(safeGrossWeightGrams, safeStoneDeductionGrams), className: 'deduction' },
    { label: 'Net alloy / other gold mass', value: Math.max(0, netWeightGrams - fineWeightGrams), className: 'alloy' },
    { label: 'Fine gold equivalent', value: fineWeightGrams, className: 'fine' }
  ]
  const weightTotal = Math.max(safeGrossWeightGrams, 0.1)

  return (
    <section className="subpage">
      <div className="subpage-head">
        <div>
          <h2>Gold Loan LOS — Assay Station & Eligibility Engine</h2>
          <p>Assay and valuation development simulator. Use synthetic test data only; no verified reading or lending decision is produced.</p>
        </div>
      </div>

      <section className="gold-kpi-grid" aria-label="Current collateral snapshot">
        <article className="gold-kpi-card">
          <span>GROSS WEIGHT</span>
          <strong>{safeGrossWeightGrams.toFixed(1)}<small> g</small></strong>
          <small>Current assay input</small>
        </article>
        <article className="gold-kpi-card">
          <span>NET COLLATERAL</span>
          <strong>{netWeightGrams.toFixed(1)}<small> g</small></strong>
          <small>After {safeStoneDeductionGrams.toFixed(1)} g deduction</small>
        </article>
        <article className="gold-kpi-card accent-violet">
          <span>FINE GOLD EQUIVALENT</span>
          <strong>{fineWeightGrams.toFixed(2)}<small> g</small></strong>
          <small>Derived from stated purity input</small>
        </article>
        <article className="gold-kpi-card accent-green">
          <span>INDICATIVE FACILITY</span>
          <strong>{indicativeFacility === null ? '—' : `₹${indicativeFacility.toLocaleString('en-IN')}`}</strong>
          <small>{indicativeFacility === null ? 'Run a valuation preview' : 'Simulator estimate · not an offer'}</small>
        </article>
      </section>

      <section className="gold-insight-grid" aria-label="Collateral analysis">
        <div className="panel gold-chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Collateral composition</h2>
              <p>Live breakdown from the current weight and purity inputs</p>
            </div>
            <span className="live-pill">INPUT-LINKED</span>
          </div>
          <div className="gold-composition-track" role="img" aria-label={`Gross weight ${safeGrossWeightGrams.toFixed(1)} grams, including ${safeStoneDeductionGrams.toFixed(1)} grams deduction and ${fineWeightGrams.toFixed(2)} grams fine gold equivalent`}>
            {weightSegments.map(segment => (
              <span
                key={segment.className}
                className={segment.className}
                style={{ width: `${segment.value / weightTotal * 100}%` }}
              />
            ))}
          </div>
          <div className="gold-chart-legend">
            {weightSegments.map(segment => (
              <div key={segment.className}>
                <i className={segment.className} />
                <span>{segment.label}</span>
                <strong>{segment.value.toFixed(2)} g</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="panel gold-chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Indicative LTV envelope</h2>
              <p>{indicativeValue === null ? 'Calculate valuation to populate the preview' : `Sample value ₹${indicativeValue.toLocaleString('en-IN')} · simulator only`}</p>
            </div>
            <Scale size={19} />
          </div>
          <div className="gold-ltv-track" role="img" aria-label={indicativeFacility === null ? 'No facility preview calculated' : `Indicative facility is ${facilityShare.toFixed(1)} percent of sample valuation`}>
            <span style={{ width: `${facilityShare}%` }} />
            <i />
          </div>
          <div className="gold-ltv-summary">
            <strong>{indicativeFacility === null ? '—' : `₹${indicativeFacility.toLocaleString('en-IN')}`}</strong>
            <span>{indicativeFacility === null ? 'Facility preview' : `${facilityShare.toFixed(1)}% of sample collateral value`}</span>
          </div>
          <small className="gold-chart-disclaimer">Static sample rate and user-entered limits; not a credit decision.</small>
        </div>
      </section>

      <div className="gold-station-grid">
        {/* LEFT COLUMN: ASSAY TERMINAL & ELIGIBILITY */}
        <div style={{ display: 'grid', gap: '18px' }}>
          {/* ASSAY TERMINAL */}
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>1. Gold Assay Simulator</h2>
                <p>Simulator only — does not ingest a physical instrument reading</p>
              </div>
              <span className="live-pill">SIMULATOR</span>
            </div>

            <div role="status" style={{ marginTop: '12px', padding: '10px 12px', border: '1px solid #f3d28b', borderRadius: '6px', background: '#fff8e8', color: '#8a5b00', fontSize: '11px', fontWeight: 700 }}>
              SIMULATED — NOT AN AUTHENTICATED DEVICE READING
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '14px' }}>
              <label>
                Assay Device
                <select value={deviceId} onChange={e => { setDeviceId(e.target.value); setVerifiedReading(null) }}>
                  <option value="DEV-XRF-001">DEV-XRF-001 (Thermo Scientific Niton DXL XRF)</option>
                  <option value="DEV-SCALE-002">DEV-SCALE-002 (Mettler Toledo ME204 Balance)</option>
                </select>
              </label>

              <label>
                Item Category
                <select value={itemType} onChange={e => { setItemType(e.target.value); setValuationResult(null) }}>
                  <option value="Gold Bangle">Gold Bangle</option>
                  <option value="Gold Necklace">Gold Necklace</option>
                  <option value="Gold Coins / Bullion">Gold Coins / Bullion</option>
                  <option value="Gold Chain">Gold Chain</option>
                </select>
              </label>

              <label>
                Simulated Gross Weight (Grams)
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  value={grossWeightGrams}
                  onChange={e => { setGrossWeightGrams(Number(e.target.value)); setValuationResult(null); setVerifiedReading(null) }}
                />
              </label>

              <label>
                Simulated Stone / Wax Deduction (Grams)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={stoneDeductionGrams}
                  onChange={e => { setStoneDeductionGrams(Number(e.target.value)); setValuationResult(null) }}
                />
              </label>

              <label style={{ gridColumn: 'span 2' }}>
                Simulated Purity Input (Fineness)
                <select value={purityBps} onChange={e => { setPurityBps(Number(e.target.value)); setValuationResult(null); setVerifiedReading(null) }}>
                  <option value={9160}>22 Karat — 916 Fineness (91.6% Pure Gold)</option>
                  <option value={9990}>24 Karat — 999 Fineness (99.9% Pure Gold)</option>
                  <option value={7500}>18 Karat — 750 Fineness (75.0% Pure Gold)</option>
                </select>
              </label>
            </div>

            <div style={{ marginTop: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button
                className="primary-button"
                onClick={handleCaptureReading}
                disabled={!hasApiSession || assayLoading || grossWeightGrams <= 0 || stoneDeductionGrams < 0 || stoneDeductionGrams > grossWeightGrams}
                title={!hasApiSession ? 'Sign in to use the protected simulator' : undefined}
              >
                <Zap size={15} /> {assayLoading ? 'Ingesting Reading...' : 'Capture & Verify Device Reading'}
              </button>
            </div>

            {verifiedReading && (
              <div className="reading-badge-box" role="status" style={{ marginTop: '14px', background: '#fff8e8', borderColor: '#f3d28b', color: '#8a5b00' }}>
                <AlertTriangle size={20} />
                <div>
                  <strong>Simulator payload signature checked (HMAC-SHA256)</strong>
                  <div>
                    Device: {verifiedReading.device_id} · Weight: {verifiedReading.gross_weight_mg / 1000}g · Purity: {verifiedReading.purity_karat}K ({verifiedReading.purity_bps / 100}%)
                  </div>
                  <small style={{ color: '#059669', fontSize: '9px' }}>
                    Simulated calibration metadata · This is not a production assay or evidence record
                  </small>
                </div>
              </div>
            )}
          </div>

          {/* VALUATION & ELIGIBILITY SCHEMES */}
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>2. Gold Valuation & Multi-Limit Eligibility Engine</h2>
                <p>Integer calculation preview using static sample rates; not an approved offer or decision</p>
              </div>
              <button className="secondary-button" onClick={handleCalculateEligibility} disabled={!hasApiSession || calcLoading || grossWeightGrams <= 0 || stoneDeductionGrams < 0 || stoneDeductionGrams > grossWeightGrams || creditLimitInr <= 0}>
                <RefreshCw size={14} /> Calculate
              </button>
            </div>

            <div role="status" style={{ marginTop: '12px', padding: '10px 12px', border: '1px solid #f3d28b', borderRadius: '6px', background: '#fff8e8', color: '#8a5b00', fontSize: '11px', fontWeight: 700 }}>
              SIMULATED RATE AND INPUTS — NOT AN APPROVED VALUATION OR CREDIT DECISION
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '14px' }}>
              <label>
                LTV Scheme
                <select value={ltvScheme} onChange={e => { setLtvScheme(Number(e.target.value)); setValuationResult(null) }}>
                  <option value={75}>75% Illustrative scheme policy</option>
                  <option value={80}>80% Illustrative scheme policy</option>
                  <option value={85}>85% Illustrative scheme policy</option>
                </select>
              </label>

              <label>
                Borrower Credit Cap (₹ INR)
                <input
                  type="number"
                  step="50000"
                  value={creditLimitInr}
                  onChange={e => { setCreditLimitInr(Number(e.target.value)); setValuationResult(null) }}
                />
              </label>
            </div>

            {valuationResult && (
              <div style={{ marginTop: '18px' }}>
                <div className="team-stats" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: '16px' }}>
                  <div>
                    <Coins size={18} />
                    <strong>₹{valuationResult.summary.eligible_loan_amount_inr.toLocaleString('en-IN')}</strong>
                    <span>Eligible Loan Amount</span>
                  </div>
                  <div>
                    <Scale size={18} />
                    <strong>{valuationResult.summary.total_fine_weight_g.toFixed(2)}g</strong>
                    <span>Fine Gold Equivalent</span>
                  </div>
                  <div>
                    <Activity size={18} />
                    <strong>₹{valuationResult.summary.total_gold_valuation_inr.toLocaleString('en-IN')}</strong>
                    <span>Sample-rate valuation</span>
                  </div>
                </div>

                {/* BINDING CONSTRAINT & COMPLIANCE BADGE */}
                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '7px', padding: '12px', fontSize: '11px', display: 'grid', gap: '6px' }}>
                  <div>
                    <strong>Binding Constraint: </strong>
                    <span className="binding-pill">{valuationResult.summary.binding_constraint}</span>
                  </div>
                  <div>
                    <strong>Regulatory Status: </strong>
                    <span style={{ color: valuationResult.summary.compliance_status === 'COMPLIANT' ? '#16a34a' : '#d97706', fontWeight: 700 }}>
                      {valuationResult.summary.compliance_status}
                    </span>
                    <span style={{ color: '#64748b', fontSize: '10px', marginLeft: '6px' }}>
                      ({valuationResult.summary.compliance_note})
                    </span>
                  </div>
                </div>

                {/* CALCULATION TRACE TABLE */}
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Limit Metric</th>
                      <th>Amount (Paise)</th>
                      <th>Amount (INR)</th>
                      <th>Constraint Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(valuationResult.limits_comparison_inr).map(([limitName, inrVal]) => (
                      <tr key={limitName}>
                        <td><strong>{limitName}</strong></td>
                        <td style={{ fontFamily: 'monospace' }}>
                          {(valuationResult.limits_comparison_paise[limitName]).toLocaleString('en-IN')} paise
                        </td>
                        <td>₹{inrVal.toLocaleString('en-IN')}</td>
                        <td>
                          {valuationResult.summary.binding_constraint === limitName ? (
                            <span className="binding-pill">BINDING LIMIT</span>
                          ) : (
                            <span style={{ color: '#16a34a', fontSize: '10px' }}>Non-binding</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: CUSTOMER KYC & KFS GENERATION */}
        <div style={{ display: 'grid', gap: '18px' }}>
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>3. Borrower KYC & Verification</h2>
                <p>Local simulator only — no identity provider is connected</p>
              </div>
            </div>

            <div style={{ display: 'grid', gap: '12px', marginTop: '14px' }}>
              <label>
                Borrower Full Name
                <input
                  value={customerName}
                  onChange={e => setCustomerName(e.target.value)}
                />
              </label>

              <label>
                Synthetic PAN test value (do not enter real customer data)
                <input
                  type="password"
                  value={panNumber}
                  onChange={e => setPanNumber(e.target.value.toUpperCase())}
                  autoComplete="off"
                  placeholder="ABCDE1234F"
                />
              </label>

              <label>
                Synthetic 12-digit Aadhaar test value (do not enter real data)
                <input
                  type="password"
                  inputMode="numeric"
                  value={aadhaarNumber}
                  onChange={e => setAadhaarNumber(e.target.value)}
                  autoComplete="off"
                  placeholder="123456789012"
                />
              </label>

              <label>
                Simulator OTP (6 digits)
                <input
                  type="password"
                  inputMode="numeric"
                  maxLength={6}
                  value={aadhaarOtp}
                  onChange={e => setAadhaarOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  autoComplete="off"
                  placeholder="Enter test OTP"
                />
              </label>

              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '10px' }}>
                <input
                  type="checkbox"
                  checked={simulatorConsent}
                  onChange={e => setSimulatorConsent(e.target.checked)}
                  style={{ marginTop: '2px' }}
                />
                I consent to a local synthetic KYC simulation. No identity provider will be contacted and no KYC verification will occur.
              </label>

              <button
                className="secondary-button"
                onClick={handleVerifyKyc}
                disabled={!hasApiSession || kycLoading}
                title={!hasApiSession ? 'Sign in to use the protected simulator' : undefined}
                style={{ marginTop: '6px' }}
              >
                <ShieldCheck size={15} /> {kycLoading ? 'Simulating...' : 'Run KYC Simulator'}
              </button>
            </div>

            {kycResult && (
              <div style={{ marginTop: '14px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '7px', padding: '12px', fontSize: '11px', display: 'grid', gap: '6px' }}>
                <div role="status" style={{ color: '#8a5b00', fontWeight: 700 }}>
                  SIMULATED — IDENTITY NOT VERIFIED BY A PROVIDER
                </div>
                <div style={{ color: '#475569' }}>
                  PAN: {kycResult.pan.masked_pan || 'REDACTED'} · Aadhaar: {kycResult.aadhaar.masked_aadhaar || 'REDACTED'}
                </div>
                <small style={{ color: '#64748b', fontSize: '9px' }}>
                  Synthetic simulator response only. No UIDAI, PAN, or other identity provider was contacted.
                </small>
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Key Fact Statement (KFS)</h2>
                <p>Document generation and signing provider are not connected</p>
              </div>
              <FileText size={20} className="text-blue-600" />
            </div>

            <div style={{ fontSize: '11px', color: '#475569', lineHeight: '1.5', marginTop: '10px' }}>
              No KFS document is generated or signed by this screen. Approved disclosures, versioned templates,
              customer consent, and provider signing evidence are not yet implemented.
            </div>

            <button
              className="secondary-button"
              style={{ marginTop: '14px', width: '100%', justifyContent: 'center' }}
              disabled
              title="Document generation and signing are not implemented"
            >
              <FileText size={15} /> KFS unavailable — signing integration not implemented
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
