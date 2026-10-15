'use client'

import Script from 'next/script'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, ArrowDownToLine, CreditCard, IndianRupee, ShieldCheck } from 'lucide-react'
import { api, type RepaymentOrder } from '@/lib/api'

interface PaymentsViewProps {
  hasApiSession: boolean
  setToast: (message: string) => void
}

interface AllocationPreview {
  payment_received_paise: number
  allocated_penal_charges_paise: number
  allocated_overdue_interest_paise: number
  allocated_current_interest_paise: number
  allocated_principal_paise: number
  surplus_advance_paise: number
  new_total_outstanding_paise: number
}

interface RazorpayPaymentResult {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

interface RazorpayPaymentFailure {
  error?: {
    description?: string
  }
}

interface RazorpayCheckoutOptions {
  key: string
  amount: number
  currency: string
  name: string
  description: string
  order_id: string
  notes: Record<string, string>
  handler: (payment: RazorpayPaymentResult) => void
  modal: { ondismiss: () => void }
}

interface RazorpayCheckout {
  open: () => void
  on: (event: 'payment.failed', handler: (response: RazorpayPaymentFailure) => void) => void
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckout
  }
}

const formatInr = (paise: number) =>
  `₹${(paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export function PaymentsView({ hasApiSession, setToast }: PaymentsViewProps) {
  const [loanId, setLoanId] = useState('')
  const [amountInr, setAmountInr] = useState('')
  const [orders, setOrders] = useState<RepaymentOrder[]>([])
  const [loadingOrders, setLoadingOrders] = useState(false)
  const [creatingOrder, setCreatingOrder] = useState(false)
  const [checkoutReady, setCheckoutReady] = useState(false)
  const [previewCount, setPreviewCount] = useState(0)
  const [allocation, setAllocation] = useState<AllocationPreview | null>(null)
  const [paymentAmount, setPaymentAmount] = useState('')
  const [principal, setPrincipal] = useState('')
  const [currentInterest, setCurrentInterest] = useState('')
  const [overdueInterest, setOverdueInterest] = useState('')
  const [penalCharges, setPenalCharges] = useState('')
  const [calculating, setCalculating] = useState(false)
  const pendingIdempotencyKey = useRef<string | null>(null)

  useEffect(() => {
    if (window.Razorpay) setCheckoutReady(true)
  }, [])

  useEffect(() => {
    if (!hasApiSession) {
      setOrders([])
      return
    }
    let active = true
    setLoadingOrders(true)
    api.getRepaymentOrders()
      .then(result => {
        if (active) setOrders(result)
      })
      .catch(error => {
        if (active) setToast(error instanceof Error ? error.message : 'Unable to load repayment orders.')
      })
      .finally(() => {
        if (active) setLoadingOrders(false)
      })
    return () => { active = false }
  }, [hasApiSession, setToast])

  const requestedVolume = useMemo(
    () => orders.reduce((total, order) => total + order.amount_paise, 0),
    [orders]
  )
  const capturedCount = orders.filter(order => order.status === 'CAPTURED').length
  const chartOrders = orders.filter(order => order.order_id).slice(0, 7).reverse()
  const maxOrderAmount = Math.max(...chartOrders.map(order => order.amount_paise), 1)

  function replaceOrder(updatedOrder: RepaymentOrder) {
    setOrders(previous => [
      updatedOrder,
      ...previous.filter(order => order.id !== updatedOrder.id)
    ])
  }

  async function handleCreateOrder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!hasApiSession) {
      setToast('Sign in before creating a repayment order.')
      return
    }
    if (!checkoutReady || !window.Razorpay) {
      setToast('Razorpay Checkout is still loading. Please try again in a moment.')
      return
    }
    const amountPaise = Math.round(Number(amountInr) * 100)
    if (!loanId.trim() || !Number.isSafeInteger(amountPaise) || amountPaise <= 0) {
      setToast('Enter a loan reference and a valid repayment amount greater than zero.')
      return
    }

    setCreatingOrder(true)
    try {
      pendingIdempotencyKey.current ??= crypto.randomUUID().replaceAll('-', '')
      const order = await api.createRepaymentOrder(
        loanId.trim(),
        amountPaise,
        pendingIdempotencyKey.current
      )
      if (!order.order_id || !order.key_id) {
        throw new Error('Razorpay did not return the test order details required to open checkout.')
      }
      pendingIdempotencyKey.current = null
      replaceOrder(order)

      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: 'AURUM',
        description: `Test repayment for ${order.loan_id}`,
        order_id: order.order_id,
        notes: { loan_id: order.loan_id },
        handler: async payment => {
          try {
            const verified = await api.verifyRepaymentPayment(
              payment.razorpay_order_id,
              payment.razorpay_payment_id,
              payment.razorpay_signature
            )
            replaceOrder(verified)
            setToast(verified.message || 'Razorpay test payment status verified.')
          } catch (error) {
            setToast(error instanceof Error ? error.message : 'Razorpay payment verification failed.')
          }
        },
        modal: {
          ondismiss: () => setToast('Checkout closed. The Razorpay test order remains available in order history.')
        }
      })
      checkout.on('payment.failed', response => {
        setToast(response.error?.description || 'Razorpay reported that the test payment failed.')
      })
      checkout.open()
      setToast('Razorpay test checkout opened. No live funds can be collected.')
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Unable to create a Razorpay test order.')
    } finally {
      setCreatingOrder(false)
    }
  }

  async function handleAllocation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!hasApiSession) {
      setToast('Sign in before running the allocation preview.')
      return
    }
    const values = [paymentAmount, principal, currentInterest, overdueInterest, penalCharges].map(Number)
    if (values.some(value => !Number.isFinite(value) || value < 0) || values[0] <= 0) {
      setToast('Enter a positive payment and non-negative sample balance values.')
      return
    }
    setCalculating(true)
    try {
      const result = await api.allocateRepayment({
        payment_amount_paise: Math.round(values[0] * 100),
        current_principal_paise: Math.round(values[1] * 100),
        accrued_interest_paise: Math.round(values[2] * 100),
        overdue_interest_paise: Math.round(values[3] * 100),
        penal_charges_paise: Math.round(values[4] * 100)
      })
      setAllocation(result)
      setPreviewCount(count => count + 1)
      setToast('Allocation preview calculated. It did not collect money or change a loan ledger.')
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Unable to calculate the allocation preview.')
    } finally {
      setCalculating(false)
    }
  }

  const allocationSegments = allocation ? [
    { label: 'Fees', amount: allocation.allocated_penal_charges_paise, tone: 'fee' },
    { label: 'Overdue interest', amount: allocation.allocated_overdue_interest_paise, tone: 'overdue' },
    { label: 'Current interest', amount: allocation.allocated_current_interest_paise, tone: 'interest' },
    { label: 'Principal', amount: allocation.allocated_principal_paise, tone: 'principal' },
    { label: 'Surplus', amount: allocation.surplus_advance_paise, tone: 'surplus' }
  ] : []

  return (
    <section className="subpage payments-view">
      <Script
        src="https://checkout.razorpay.com/v1/checkout.js"
        strategy="afterInteractive"
        onLoad={() => setCheckoutReady(true)}
        onError={() => setToast('Razorpay Checkout could not load. Check the network and content-security policy.')}
      />
      <div className="subpage-head">
        <div>
          <h2>Repayment operations</h2>
          <p>Razorpay test checkout and payment verification. No live funds or loan ledger entries are involved.</p>
        </div>
        <span className="payment-mode-badge"><span /> RAZORPAY TEST MODE · NO LIVE CHARGE</span>
      </div>

      <div className="payment-kpi-grid" aria-label="Razorpay test payment activity">
        <article className="payment-kpi-card">
          <div className="payment-kpi-icon blue"><CreditCard size={17} /></div>
          <span>TEST ORDERS</span>
          <strong>{orders.length}</strong>
          <small>{loadingOrders ? 'Refreshing workspace records…' : 'Saved to this workspace'}</small>
        </article>
        <article className="payment-kpi-card">
          <div className="payment-kpi-icon violet"><IndianRupee size={17} /></div>
          <span>TEST ORDER VOLUME</span>
          <strong>{formatInr(requestedVolume)}</strong>
          <small>Not live collections</small>
        </article>
        <article className="payment-kpi-card">
          <div className="payment-kpi-icon green"><ShieldCheck size={17} /></div>
          <span>PROVIDER CAPTURED</span>
          <strong>{capturedCount}</strong>
          <small>Razorpay test mode only</small>
        </article>
        <article className="payment-kpi-card">
          <div className="payment-kpi-icon amber"><Activity size={17} /></div>
          <span>ALLOCATION PREVIEWS</span>
          <strong>{previewCount}</strong>
          <small>This page session · illustrative only</small>
        </article>
      </div>

      <div className="payment-insight-grid">
        <div className="panel payment-chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Order request pulse</h2>
              <p>Recent Razorpay test orders · saved workspace history</p>
            </div>
            <span className="payment-chart-legend"><i /> Test orders</span>
          </div>
          <svg className="payment-bars" viewBox="0 0 360 128" role="img" aria-label={`${chartOrders.length} recent Razorpay test orders`}>
            <line x1="16" y1="96" x2="344" y2="96" />
            {chartOrders.length ? chartOrders.map((order, index) => {
              const height = Math.max(6, order.amount_paise / maxOrderAmount * 70)
              const x = 30 + index * 46
              return (
                <g key={order.id}>
                  <rect x={x} y={96 - height} width="22" height={height} rx="5" />
                  <text x={x + 11} y="116" textAnchor="middle">{index + 1}</text>
                </g>
              )
            }) : (
              <text className="chart-empty-label" x="180" y="60" textAnchor="middle">Create a Razorpay test order to populate this chart</text>
            )}
          </svg>
          <div className="payment-chart-foot">
            <span>Oldest</span><span>Most recent</span>
          </div>
        </div>

        <form className="panel payment-form" onSubmit={handleCreateOrder}>
          <div className="panel-heading">
            <div>
              <h2>Create repayment order</h2>
              <p>Opens Razorpay Checkout in test mode</p>
            </div>
            <ArrowDownToLine size={19} />
          </div>
          <label>
            Loan reference
            <input value={loanId} onChange={event => setLoanId(event.target.value)} placeholder="Enter a test loan reference" required />
          </label>
          <label>
            Repayment amount (₹ INR)
            <input type="number" min="1" step="0.01" value={amountInr} onChange={event => setAmountInr(event.target.value)} placeholder="e.g. 25000" required />
          </label>
          <button className="primary-button payment-submit" type="submit" disabled={!hasApiSession || !checkoutReady || creatingOrder}>
            <CreditCard size={15} /> {creatingOrder ? 'Connecting to Razorpay…' : checkoutReady ? 'Pay with Razorpay (Test)' : 'Loading Razorpay Checkout…'}
          </button>
          <small className="payment-form-note">Test cards/UPI only. Payment status is verified server-side; this workspace does not post to a loan ledger.</small>
        </form>
      </div>

      <div className="payment-lower-grid">
        <div className="panel payment-orders-panel">
          <div className="panel-heading">
            <div>
              <h2>Payment order history</h2>
              <p>Workspace records · tenant-scoped server storage</p>
            </div>
            <span className="session-count">{orders.length} orders</span>
          </div>
          {orders.length ? (
            <div className="payment-order-list">
              {orders.map(order => (
                <div className="payment-order-row" key={order.id}>
                  <div className="payment-order-mark"><CreditCard size={15} /></div>
                  <div className="payment-order-main">
                    <strong>{order.loan_id}</strong>
                    <span>{order.order_id || 'Order creation needs reconciliation'}</span>
                  </div>
                  <strong className="payment-order-amount">{formatInr(order.amount_paise)}</strong>
                  <span className={`payment-sim-status ${order.status === 'CAPTURED' ? 'captured' : ''}`}>{order.status.replaceAll('_', ' ')}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="payment-empty-state">
              <CreditCard size={22} />
              <strong>{loadingOrders ? 'Loading workspace payment history…' : 'No Razorpay test orders yet'}</strong>
              <span>Orders created in test mode are saved here and remain separate from loan accounting.</span>
            </div>
          )}
        </div>

        <form className="panel payment-form allocation-form" onSubmit={handleAllocation}>
          <div className="panel-heading">
            <div>
              <h2>Waterfall allocation preview</h2>
              <p>Fee → overdue interest → interest → principal</p>
            </div>
            <Activity size={19} />
          </div>
          <div className="allocation-input-grid">
            <label>Payment amount (₹)<input type="number" min="0.01" step="0.01" value={paymentAmount} onChange={event => setPaymentAmount(event.target.value)} required /></label>
            <label>Principal balance (₹)<input type="number" min="0" step="0.01" value={principal} onChange={event => setPrincipal(event.target.value)} required /></label>
            <label>Current interest (₹)<input type="number" min="0" step="0.01" value={currentInterest} onChange={event => setCurrentInterest(event.target.value)} required /></label>
            <label>Overdue interest (₹)<input type="number" min="0" step="0.01" value={overdueInterest} onChange={event => setOverdueInterest(event.target.value)} required /></label>
            <label>Penal charges (₹)<input type="number" min="0" step="0.01" value={penalCharges} onChange={event => setPenalCharges(event.target.value)} required /></label>
          </div>
          <button className="secondary-button" type="submit" disabled={!hasApiSession || calculating}>
            <Activity size={15} /> {calculating ? 'Calculating…' : 'Preview allocation'}
          </button>
          {allocation && (
            <div className="allocation-result" role="status">
              <div className="allocation-result-head">
                <span>Illustrative payment</span><strong>{formatInr(allocation.payment_received_paise)}</strong>
              </div>
              <div className="allocation-stack" aria-label="Repayment allocation breakdown">
                {allocationSegments.filter(segment => segment.amount > 0).map(segment => (
                  <span key={segment.tone} className={segment.tone} style={{ flexGrow: segment.amount }} title={`${segment.label}: ${formatInr(segment.amount)}`} />
                ))}
              </div>
              <div className="allocation-legend">
                {allocationSegments.map(segment => (
                  <div key={segment.tone}><i className={segment.tone} /><span>{segment.label}</span><strong>{formatInr(segment.amount)}</strong></div>
                ))}
              </div>
              <div className="allocation-result-total"><span>Illustrative balance after allocation</span><strong>{formatInr(allocation.new_total_outstanding_paise)}</strong></div>
              <small>Preview only. No payment or loan balance was posted or updated.</small>
            </div>
          )}
        </form>
      </div>
    </section>
  )
}
