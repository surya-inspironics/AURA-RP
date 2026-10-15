'use client'

import { useState } from 'react'
import {
  ShieldCheck, Lock, CheckCircle2, AlertTriangle, CreditCard,
  Building2, Activity, ArrowRight, RefreshCw, Zap, Users
} from 'lucide-react'
import { api } from '@/lib/api'

interface VaultServicingProps {
  setToast: (msg: string) => void
  hasApiSession: boolean
}

export function VaultServicingView({ setToast, hasApiSession }: VaultServicingProps) {
  const [activeTab, setActiveTab] = useState<'vault' | 'disbursal' | 'repayment' | 'mtm'>('vault')

  // Vault packet state
  const [loanId, setLoanId] = useState('')
  const [custodian1, setCustodian1] = useState('')
  const [custodian2, setCustodian2] = useState('')
  const [rackId, setRackId] = useState('')
  const [itemCount, setItemCount] = useState(1)
  const [netWeightMg, setNetWeightMg] = useState(0)
  const [sealedPackets, setSealedPackets] = useState<any[]>([])

  // Disbursal state
  const [beneficiaryName, setBeneficiaryName] = useState('')
  const [beneficiaryAccount, setBeneficiaryAccount] = useState('')
  const [beneficiaryIfsc, setBeneficiaryIfsc] = useState('')
  const [disbursalAmountInr, setDisbursalAmountInr] = useState(0)
  const [makerId, setMakerId] = useState('')
  const [checkerId, setCheckerId] = useState('')
  const [disbursalResult, setDisbursalResult] = useState<any>(null)
  const [disbursalLoading, setDisbursalLoading] = useState(false)

  // Repayment & Waterfall state
  const [repaymentAmountInr, setRepaymentAmountInr] = useState(0)
  const [repaymentPrincipalInr, setRepaymentPrincipalInr] = useState(0)
  const [repaymentInterestInr, setRepaymentInterestInr] = useState(0)
  const [repaymentOverdueInr, setRepaymentOverdueInr] = useState(0)
  const [repaymentPenalInr, setRepaymentPenalInr] = useState(0)
  const [waterfallResult, setWaterfallResult] = useState<any>(null)
  const [webhookSimResult, setWebhookSimResult] = useState<any>(null)
  const [pgLoading, setPgLoading] = useState(false)

  // MTM state
  const [mtmOutstandingInr, setMtmOutstandingInr] = useState(0)
  const [mtmWeightGrams, setMtmWeightGrams] = useState(0)
  const [mtmPurityBps, setMtmPurityBps] = useState(9160)
  const [mtmResult, setMtmResult] = useState<any>(null)
  const [mtmLoading, setMtmLoading] = useState(false)

  // 1. Vault Packet Sealing
  async function handleSealPacket() {
    if (!hasApiSession) {
      setToast('Sign in to use protected vault simulators.')
      return
    }
    if (!loanId.trim() || !rackId.trim() || !custodian1 || !custodian2 || custodian1 === custodian2 || itemCount < 1 || netWeightMg < 1) {
      setToast('Enter a loan ID, rack, distinct custodians, item count, and positive net weight.')
      return
    }
    try {
      const packet = await api.sealVaultPacket({
        loan_id: loanId,
        custodian_1_id: custodian1,
        custodian_2_id: custodian2,
        vault_rack_id: rackId,
        item_count: itemCount,
        net_weight_mg: netWeightMg
      })
      setSealedPackets(prev => [{
        barcode: packet.barcode,
        loan_id: packet.loan_id,
        rack_id: packet.vault_rack_id,
        item_count: packet.item_count,
        net_weight_g: packet.net_weight_mg / 1000,
        status: packet.status,
        custodians: `${custodian1} & ${custodian2}`
      }, ...prev])
      setToast(`SIMULATED — NO PHYSICAL CUSTODY EVENT RECORDED (${packet.barcode})`)
    } catch (err: any) {
      setToast(err.message || 'Sealing failed')
    }
  }

  // 2. Disbursal Execution
  async function handleExecuteDisbursal() {
    if (!hasApiSession) {
      setToast('Sign in to use protected payout simulators.')
      return
    }
    if (!loanId.trim() || !beneficiaryName.trim() || !beneficiaryAccount.trim() || !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(beneficiaryIfsc) || disbursalAmountInr <= 0 || !makerId || !checkerId || makerId === checkerId) {
      setToast('Complete valid payout details and select different maker and checker identities.')
      return
    }
    setDisbursalLoading(true)
    try {
      const payout = await api.executeDisbursal({
        loan_id: loanId,
        amount_paise: disbursalAmountInr * 100,
        beneficiary_account: beneficiaryAccount,
        beneficiary_ifsc: beneficiaryIfsc,
        beneficiary_name: beneficiaryName,
        maker_id: makerId,
        checker_id: checkerId,
        idempotency_key: `disb_${loanId}_${Date.now()}`
      })
      setDisbursalResult(payout)
      setToast(payout.is_simulated
        ? 'SIMULATED — NO MONEY TRANSFERRED'
        : `Disbursal status: ${payout.status}`)
    } catch (err: any) {
      setToast(err.message || 'Disbursal failed')
    } finally {
      setDisbursalLoading(false)
    }
  }

  // 3. Repayment Waterfall Calculation
  async function handleWaterfallAllocation() {
    if (!hasApiSession) {
      setToast('Sign in to use protected servicing simulators.')
      return
    }
    if (repaymentAmountInr <= 0) {
      setToast('Enter a repayment amount greater than zero.')
      return
    }
    if ([repaymentPrincipalInr, repaymentInterestInr, repaymentOverdueInr, repaymentPenalInr].some(value => value < 0)) {
      setToast('Sample balances and charges cannot be negative.')
      return
    }
    setPgLoading(true)
    try {
      const res = await api.allocateRepayment({
        payment_amount_paise: repaymentAmountInr * 100,
        current_principal_paise: Math.round(repaymentPrincipalInr * 100),
        accrued_interest_paise: Math.round(repaymentInterestInr * 100),
        overdue_interest_paise: Math.round(repaymentOverdueInr * 100),
        penal_charges_paise: Math.round(repaymentPenalInr * 100)
      })
      setWaterfallResult(res)
      setToast('Illustrative allocation preview calculated. No payment or ledger entry was created.')
    } catch (err: any) {
      setToast(err.message || 'Allocation failed')
    } finally {
      setPgLoading(false)
    }
  }

  // 4. MTM LTV Revaluation
  async function handleEvaluateMtm() {
    if (!hasApiSession) {
      setToast('Sign in to use protected collections simulators.')
      return
    }
    if (!loanId.trim() || mtmOutstandingInr <= 0 || mtmWeightGrams <= 0) {
      setToast('Enter a loan reference, positive outstanding balance, and positive gold weight.')
      return
    }
    setMtmLoading(true)
    try {
      const res = await api.evaluateMtm({
        loan_id: loanId,
        total_outstanding_paise: Math.round(mtmOutstandingInr * 100),
        net_gold_weight_mg: Math.round(mtmWeightGrams * 1000),
        purity_bps: mtmPurityBps
      })
      setMtmResult(res)
      setToast(`Illustrative MTM calculation: ${res.current_ltv_pct}% LTV (${res.risk_tier}); no workflow was triggered.`)
    } catch (err: any) {
      setToast(err.message || 'MTM evaluation failed')
    } finally {
      setMtmLoading(false)
    }
  }

  return (
    <section className="subpage vault-servicing-view">
      <div className="subpage-head">
        <div>
          <h2>Vault Custody, Disbursals & LMS Servicing</h2>
          <p>Local workflow simulators only; these controls are not connected to physical vault, payment, servicing, or collections providers.</p>
        </div>
      </div>

      <div role="status" style={{ padding: '10px 12px', border: '1px solid #f3d28b', borderRadius: '6px', background: '#fff8e8', color: '#8a5b00', fontSize: '11px', fontWeight: 700 }}>
        DEVELOPMENT SIMULATORS ONLY — no bank payment, repayment, physical vault event, ledger posting, notice, or auction is performed.
      </div>

      <div className="vault-kpi-grid" aria-label="Simulated operations in this session">
        <article className="gold-kpi-card">
          <span>PACKET PREVIEWS</span>
          <strong>{sealedPackets.length}</strong>
          <small>In-memory records only</small>
        </article>
        <article className="gold-kpi-card accent-violet">
          <span>PAYOUT PREVIEW</span>
          <strong>{disbursalResult ? `₹${(disbursalResult.amount_paise / 100).toLocaleString('en-IN')}` : '—'}</strong>
          <small>No funds transferred</small>
        </article>
        <article className="gold-kpi-card accent-green">
          <span>ALLOCATION PREVIEW</span>
          <strong>{waterfallResult ? `₹${(waterfallResult.payment_received_paise / 100).toLocaleString('en-IN')}` : '—'}</strong>
          <small>No repayment collected</small>
        </article>
        <article className="gold-kpi-card">
          <span>COLLATERAL HEALTH</span>
          <strong>{mtmResult ? `${mtmResult.current_ltv_pct}% LTV` : '—'}</strong>
          <small>{mtmResult ? `${mtmResult.risk_tier} · illustrative` : 'Run a revaluation preview'}</small>
        </article>
      </div>

      <div className="panel vault-session-chart">
        <div className="panel-heading">
          <div>
            <h2>Session workflow signals</h2>
            <p>Actions performed in this browser session only — not a loan portfolio or persisted workflow</p>
          </div>
          <Activity size={18} />
        </div>
        <div className="vault-signal-grid">
          {[
            { label: 'Custody preview', count: sealedPackets.length, tone: 'blue' },
            { label: 'Payout preview', count: Number(Boolean(disbursalResult)), tone: 'violet' },
            { label: 'Repayment preview', count: Number(Boolean(waterfallResult)), tone: 'green' },
            { label: 'MTM preview', count: Number(Boolean(mtmResult)), tone: 'amber' }
          ].map(signal => (
            <div className="vault-signal" key={signal.label}>
              <div><span>{signal.label}</span><strong>{signal.count}</strong></div>
              <div className="vault-signal-track"><i className={signal.tone} style={{ width: signal.count ? '100%' : '0%' }} /></div>
            </div>
          ))}
        </div>
      </div>

      {/* WORKFLOW NAVIGATION TABS */}
      <div className="tab-row">
        <button
          className={`tab-btn ${activeTab === 'vault' ? 'active' : ''}`}
          onClick={() => setActiveTab('vault')}
        >
          1. Vault Custody (Dual Control)
        </button>
        <button
          className={`tab-btn ${activeTab === 'disbursal' ? 'active' : ''}`}
          onClick={() => setActiveTab('disbursal')}
        >
          2. Payout Simulation (No Money Movement)
        </button>
        <button
          className={`tab-btn ${activeTab === 'repayment' ? 'active' : ''}`}
          onClick={() => setActiveTab('repayment')}
        >
          3. Repayment Allocation Simulator
        </button>
        <button
          className={`tab-btn ${activeTab === 'mtm' ? 'active' : ''}`}
          onClick={() => setActiveTab('mtm')}
        >
          4. MTM LTV & Collections
        </button>
      </div>

      {/* TAB 1: VAULT CUSTODY DUAL CONTROL */}
      {activeTab === 'vault' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr .8fr', gap: '18px' }}>
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Vault Custody Simulator</h2>
                <p>In-memory test record only; officer IDs are not authenticated and no physical packet is sealed.</p>
              </div>
              <ShieldCheck size={20} className="text-emerald-600" />
            </div>

            <div role="status" style={{ marginTop: '12px', padding: '10px 12px', border: '1px solid #f3d28b', borderRadius: '6px', background: '#fff8e8', color: '#8a5b00', fontSize: '11px', fontWeight: 700 }}>
              SIMULATED — NO PHYSICAL CUSTODY EVENT RECORDED
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '14px' }}>
              <label>
                Loan ID / Case
                <input value={loanId} onChange={e => setLoanId(e.target.value)} placeholder="Enter loan / case reference" required />
              </label>

              <label>
                Vault Rack / Bay Location
                <input value={rackId} onChange={e => setRackId(e.target.value)} placeholder="Vault rack / bay" required />
              </label>

              <label>
                Custodian 1 (Officer A)
                  <select value={custodian1} onChange={e => setCustodian1(e.target.value)}>
                  <option value="">Select custodian</option>
                  <option value="custodian_maya_chen">Maya Chen (Vault Incharge)</option>
                  <option value="custodian_samir_patel">Samir Patel (Operations Officer)</option>
                  <option value="custodian_alicia_rossi">Alicia Rossi (Branch Manager)</option>
                </select>
              </label>

              <label>
                Custodian 2 (Officer B - Must Differ)
                <select value={custodian2} onChange={e => setCustodian2(e.target.value)}>
                  <option value="">Select a different custodian</option>
                  <option value="custodian_samir_patel">Samir Patel (Operations Officer)</option>
                  <option value="custodian_maya_chen">Maya Chen (Vault Incharge)</option>
                  <option value="custodian_alicia_rossi">Alicia Rossi (Branch Manager)</option>
                </select>
              </label>

              <label>
                Pledged Item Count
                <input
                  type="number"
                  min="1"
                  value={itemCount}
                  onChange={e => setItemCount(Number(e.target.value))}
                />
              </label>

              <label>
                Net Gold Weight (Milligrams)
                <input
                  type="number"
                  min="1"
                  value={netWeightMg}
                  onChange={e => setNetWeightMg(Number(e.target.value))}
                />
              </label>
            </div>

            <button
              className="primary-button"
              style={{ marginTop: '16px' }}
              onClick={handleSealPacket}
              disabled={!hasApiSession || !loanId.trim() || !rackId.trim() || !custodian1 || !custodian2 || custodian1 === custodian2 || itemCount < 1 || netWeightMg < 1}
            >
              <Lock size={15} /> Create Simulated Packet Record
            </button>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Simulated Packet Records</h2>
                <p>Not connected to or representative of physical vault inventory</p>
              </div>
            </div>

            <div className="file-list">
              {sealedPackets.map(pkt => (
                <div className="file-row" key={pkt.barcode}>
                  <div className="file-icon"><Lock size={16} /></div>
                  <div>
                    <strong>{pkt.barcode}</strong>
                    <span>{pkt.rack_id} · {pkt.item_count} items ({pkt.net_weight_g}g)</span>
                    <small style={{ color: '#64748b', fontSize: '9px' }}>Selected demo identities: {pkt.custodians}</small>
                  </div>
                  <span className="status amber"><span /> {pkt.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DISBURSAL MAKER-CHECKER (MONEY OUT) */}
      {activeTab === 'disbursal' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr .8fr', gap: '18px' }}>
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Payout Simulator (No Money Out)</h2>
                <p>Local response simulator only; no bank settlement or ledger posting is available.</p>
              </div>
              <Building2 size={20} className="text-blue-600" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '14px' }}>
              <label>
                Beneficiary Name
                <input value={beneficiaryName} onChange={e => setBeneficiaryName(e.target.value)} placeholder="Beneficiary name" required />
              </label>

              <label>
                Sanctioned Amount (₹ INR)
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={disbursalAmountInr}
                  onChange={e => setDisbursalAmountInr(Number(e.target.value))}
                />
              </label>

              <label>
                Bank Account Number
                <input
                  type="password"
                  autoComplete="off"
                  placeholder="Enter bank account"
                  value={beneficiaryAccount}
                  onChange={e => setBeneficiaryAccount(e.target.value)}
                />
              </label>

              <label>
                Bank IFSC Code
                <input value={beneficiaryIfsc} onChange={e => setBeneficiaryIfsc(e.target.value.toUpperCase())} placeholder="e.g. ABCD0123456" maxLength={11} required />
              </label>

              <label>
                Maker (Loan Officer)
                <select value={makerId} onChange={e => setMakerId(e.target.value)}>
                  <option value="">Select maker</option>
                  <option value="maker_analyst_01">James Okafor (Credit Analyst)</option>
                  <option value="maker_officer_02">Maya Chen (Loan Officer)</option>
                </select>
              </label>

              <label>
                Checker (Approving Manager - Must Differ)
                <select value={checkerId} onChange={e => setCheckerId(e.target.value)}>
                  <option value="">Select a different checker</option>
                  <option value="checker_manager_02">Alicia Rossi (Branch Manager)</option>
                  <option value="checker_admin_01">Jordan Davies (Administrator)</option>
                </select>
              </label>
            </div>

            <button
              className="primary-button"
              style={{ marginTop: '16px' }}
              onClick={handleExecuteDisbursal}
              disabled={!hasApiSession || disbursalLoading || !loanId.trim() || !beneficiaryName.trim() || !beneficiaryAccount.trim() || !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(beneficiaryIfsc) || disbursalAmountInr <= 0 || !makerId || !checkerId || makerId === checkerId}
            >
              <CreditCard size={15} /> {disbursalLoading ? 'Simulating...' : 'Create Simulated Payout Record'}
            </button>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Simulated Payout Details</h2>
                <p>No connection to NPCI or core banking</p>
              </div>
            </div>

            {disbursalResult ? (
              <div style={{ marginTop: '14px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '7px', padding: '14px', display: 'grid', gap: '8px', fontSize: '11px' }}>
                <div role="status" style={{ color: disbursalResult.is_simulated ? '#8a5b00' : '#166534', fontWeight: 700, fontSize: '12px' }}>
                  {disbursalResult.is_simulated
                    ? 'SIMULATED — NO MONEY TRANSFERRED'
                    : `Disbursal status: ${disbursalResult.status}`}
                </div>
                <div><strong>Payout ID:</strong> {disbursalResult.payout_id}</div>
                {disbursalResult.utr_number && (
                  <div><strong>Provider reference:</strong> <span style={{ fontFamily: 'monospace' }}>{disbursalResult.utr_number}</span></div>
                )}
                <div><strong>Beneficiary:</strong> {disbursalResult.beneficiary_name} ({disbursalResult.beneficiary_account})</div>
                <div><strong>Amount:</strong> ₹{(disbursalResult.amount_paise / 100).toLocaleString('en-IN')}</div>
                <div><strong>Dual Approval:</strong> Maker: {disbursalResult.maker_id} · Checker: {disbursalResult.checker_id}</div>
                <small style={{ color: '#64748b', fontSize: '9px' }}>
                  {disbursalResult.is_simulated
                    ? 'In-memory simulator response only. No bank was contacted and no loan ledger was updated.'
                    : 'Provider result requires reconciliation before ledger posting.'}
                </small>
              </div>
            ) : (
              <div style={{ color: '#64748b', fontSize: '11px', marginTop: '20px' }}>
                No simulated payout record in this session.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: SERVICING & REPAYMENT (MONEY IN) */}
      {activeTab === 'repayment' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr .8fr', gap: '18px' }}>
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Repayment Allocation Calculator</h2>
                <p>Illustrative allocation only; does not collect money or update a loan balance.</p>
              </div>
              <Activity size={20} className="text-emerald-600" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '14px' }}>
              <label>
                Repayment Amount (₹ INR)
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={repaymentAmountInr}
                  onChange={e => setRepaymentAmountInr(Number(e.target.value))}
                />
              </label>

              <label>
                Payment Channel
                <select defaultValue="UPI">
                  <option value="UPI">UPI (Instant Settlement)</option>
                  <option value="NETBANKING">NetBanking / Mandate</option>
                  <option value="CASH_DESK">Branch Cash Desk</option>
                </select>
              </label>
              <label>
                Current principal balance (₹ INR)
                <input type="number" min="0" step="0.01" value={repaymentPrincipalInr} onChange={e => setRepaymentPrincipalInr(Number(e.target.value))} />
              </label>
              <label>
                Current accrued interest (₹ INR)
                <input type="number" min="0" step="0.01" value={repaymentInterestInr} onChange={e => setRepaymentInterestInr(Number(e.target.value))} />
              </label>
              <label>
                Overdue interest (₹ INR)
                <input type="number" min="0" step="0.01" value={repaymentOverdueInr} onChange={e => setRepaymentOverdueInr(Number(e.target.value))} />
              </label>
              <label>
                Penal charges (₹ INR)
                <input type="number" min="0" step="0.01" value={repaymentPenalInr} onChange={e => setRepaymentPenalInr(Number(e.target.value))} />
              </label>
            </div>

            <button
              className="primary-button"
              style={{ marginTop: '16px' }}
              onClick={handleWaterfallAllocation}
              disabled={!hasApiSession || pgLoading || repaymentAmountInr <= 0}
            >
              <Activity size={15} /> Preview Allocation (No Ledger Posting)
            </button>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Simulated Allocation Breakdown</h2>
                <p>Calculated from illustrative sample balances; no loan ledger is changed.</p>
              </div>
            </div>

            {waterfallResult ? (
              <div style={{ marginTop: '14px', display: 'grid', gap: '8px', fontSize: '11px' }}>
                <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
                  <strong>Simulated amount:</strong> ₹{(waterfallResult.payment_received_paise / 100).toLocaleString('en-IN')}
                </div>
                <div style={{ display: 'grid', gap: '4px', paddingLeft: '6px' }}>
                  <div>1. Penal Charges Cleared: <strong>₹{(waterfallResult.allocated_penal_charges_paise / 100).toLocaleString('en-IN')}</strong></div>
                  <div>2. Overdue Interest Cleared: <strong>₹{(waterfallResult.allocated_overdue_interest_paise / 100).toLocaleString('en-IN')}</strong></div>
                  <div>3. Current Interest Cleared: <strong>₹{(waterfallResult.allocated_current_interest_paise / 100).toLocaleString('en-IN')}</strong></div>
                  <div>4. Principal Reduced By: <strong>₹{(waterfallResult.allocated_principal_paise / 100).toLocaleString('en-IN')}</strong></div>
                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '6px', marginTop: '4px' }}>
                    <strong>Remaining Outstanding Balance:</strong> ₹{(waterfallResult.new_total_outstanding_paise / 100).toLocaleString('en-IN')}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: '#64748b', fontSize: '11px', marginTop: '20px' }}>
                Enter payment amount and click compute to preview the repayment waterfall distribution.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: MTM LTV & COLLECTIONS */}
      {activeTab === 'mtm' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr .8fr', gap: '18px' }}>
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Illustrative MTM Calculator</h2>
                <p>One-off calculation using static sample rates; no daily valuation or margin-call workflow runs.</p>
              </div>
              <Activity size={20} className="text-amber-600" />
            </div>

            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '10px', lineHeight: '1.5' }}>
              LTV thresholds and cure periods shown here are illustrative lender-policy inputs, not a verified regulatory rule.
              This screen does not send notices or initiate an auction workflow.
            </div>

            <div className="vault-mtm-inputs">
              <label>
                Loan / case reference
                <input value={loanId} onChange={e => setLoanId(e.target.value)} placeholder="Enter loan / case reference" />
              </label>
              <label>
                Total outstanding (₹ INR)
                <input type="number" min="0.01" step="0.01" value={mtmOutstandingInr} onChange={e => setMtmOutstandingInr(Number(e.target.value))} />
              </label>
              <label>
                Net gold weight (grams)
                <input type="number" min="0.01" step="0.01" value={mtmWeightGrams} onChange={e => setMtmWeightGrams(Number(e.target.value))} />
              </label>
              <label>
                Stated purity
                <select value={mtmPurityBps} onChange={e => setMtmPurityBps(Number(e.target.value))}>
                  <option value={9990}>24K · 999 fineness</option>
                  <option value={9160}>22K · 916 fineness</option>
                  <option value={7500}>18K · 750 fineness</option>
                </select>
              </label>
            </div>
            <button
              className="primary-button"
              style={{ marginTop: '16px' }}
              onClick={handleEvaluateMtm}
              disabled={!hasApiSession || mtmLoading || !loanId.trim() || mtmOutstandingInr <= 0 || mtmWeightGrams <= 0}
            >
              <RefreshCw size={15} /> Run MTM Revaluation Probe
            </button>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Revaluation Outcome</h2>
                <p>Collateral health and margin risk assessment</p>
              </div>
            </div>

            {mtmResult ? (
              <div style={{ marginTop: '14px', display: 'grid', gap: '8px', fontSize: '11px' }}>
                <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
                  <strong>Current LTV:</strong>{' '}
                  <span style={{ fontSize: '16px', fontWeight: 800, color: mtmResult.requires_margin_call ? '#991b1b' : '#16a34a' }}>
                    {mtmResult.current_ltv_pct}%
                  </span>
                </div>
                <div><strong>Collateral Market Value:</strong> ₹{mtmResult.current_market_value_inr.toLocaleString('en-IN')}</div>
                <div><strong>Total Debt Outstanding:</strong> ₹{mtmResult.total_outstanding_inr.toLocaleString('en-IN')}</div>
                <div>
                  <strong>Risk Tier:</strong>{' '}
                  <span className={`status ${mtmResult.risk_tier === 'HEALTHY' ? 'green' : 'red'}`}>
                    <span /> {mtmResult.risk_tier}
                  </span>
                </div>
                {mtmResult.requires_margin_call && (
                  <div style={{ background: '#fee2e2', color: '#991b1b', padding: '8px 10px', borderRadius: '6px', fontWeight: 700 }}>
                    ⚠ MARGIN CALL TRIGGERED: Shortfall amount ₹{mtmResult.margin_shortfall_inr.toLocaleString('en-IN')} must be deposited within 7 days.
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: '#64748b', fontSize: '11px', marginTop: '20px' }}>
                Click run probe to evaluate live collateral market value against loan balances.
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
