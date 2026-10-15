// AURA Enterprise SaaS Frontend API Client (TypeScript)
// Communicates with the Python FastAPI Backend (/api/v1)

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

export interface CaseItem {
  id: string
  tenant_id: string
  case_number: string
  customer_name: string
  product_type: string
  requested_amount: number
  tenure_months: number
  purpose?: string
  status: string
  priority: string
  owner_name: string
  owner_initials: string
  sla_hours: number
  sla_due_at?: string
  created_at: string
  updated_at: string
  files_count?: number
}

export interface EvidenceItem {
  id: string
  case_id: string
  file_name: string
  file_type: string
  file_size_bytes: number
  sha256_checksum: string
  validation_status: string
  uploaded_by_name: string
  created_at: string
}

export interface ValidationFinding {
  id: string
  rule_id: string
  rule_name: string
  outcome: string
  explanation: string
  severity: string
  executed_at: string
}

export interface DecisionItem {
  id: string
  case_id: string
  actor_name: string
  outcome: string
  eligible_amount?: number
  interest_rate?: number
  rationale: string
  rule_version: string
  created_at: string
}

export interface AuditEventItem {
  id: string
  actor_name: string
  action: string
  entity_type: string
  entity_id: string
  correlation_id?: string
  metadata: Record<string, any>
  prev_hash: string
  current_hash: string
  created_at: string
}

export interface AnalyticsDashboard {
  kpis: {
    open_cases: number
    pending_validation: number
    awaiting_decision: number
    open_exceptions: number
    total_cases: number
    sla_compliance_rate: number
    validation_pass_rate: number
    avg_processing_hours: number
    active_filters_count: number
  }
  workflow: {
    in_progress: number
    ready_for_review: number
    awaiting_evidence: number
    approved: number
    rejected: number
    exceptions: number
  }
  funnel: Record<string, number>
  trends: Array<{
    date: string
    submitted: number
    validated: number
    decided: number
  }>
  reviewers_workload: Record<string, number>
  sla_performance: {
    on_time: number
    at_risk: number
    overdue: number
  }
}

export interface TeamMember {
  id: string
  user_id: string
  email: string
  full_name: string
  avatar_initials: string
  role: string
  is_active: boolean
  created_at: string
}

export interface BillingSummary {
  plan_name: string
  monthly_price: number
  cases_used: number
  cases_limit: number
  storage_used_gb: number
  storage_limit_gb: number
  seats_used: number
  seats_limit: number
  status: string
  renewal_date: string
  invoices: Array<{
    id: string
    date: string
    amount: string
    status: string
  }>
}

export interface AdapterConfigField {
  key: string
  configured: boolean
}

export interface AdapterStatus {
  name: string
  category: string
  description: string
  mode: 'MOCK' | 'SANDBOX' | 'PRODUCTION'
  health: 'HEALTHY' | 'SIMULATED' | 'DEGRADED' | 'UNAVAILABLE' | 'NOT_CONFIGURED'
  latency_ms: number
  last_health_check?: string
  last_error?: string
  simulated_failure?: string
  is_test_mode: boolean
  required_configs: AdapterConfigField[]
}

export interface ValuationResponse {
  summary: {
    total_items: number
    total_gross_weight_mg: number
    total_gross_weight_g: number
    total_stone_deduction_mg: number
    total_net_weight_mg: number
    total_net_weight_g: number
    total_fine_weight_mg: number
    total_fine_weight_g: number
    total_gold_valuation_paise: number
    total_gold_valuation_inr: number
    applied_ltv_pct: number
    eligible_loan_amount_paise: number
    eligible_loan_amount_inr: number
    binding_constraint: string
    compliance_status: string
    compliance_note: string
    rate_version: string
    gold_rate_per_gram_paise: number
  }
  limits_comparison_paise: Record<string, number>
  limits_comparison_inr: Record<string, number>
  item_traces: Array<{
    item_number: number
    item_type: string
    gross_weight_mg: number
    stone_deduction_mg: number
    net_weight_mg: number
    purity_bps: number
    purity_karat: number
    fine_weight_mg: number
    item_valuation_paise: number
    item_valuation_inr: number
  }>
}

export interface ApiAuthResponse {
  access_token: string
  token_type: string
  user: { id: string; email: string; name: string; role: string }
  tenant: { id: string; name: string; slug: string }
}

export interface ApiSessionProfile {
  user: ApiAuthResponse['user']
  tenant: ApiAuthResponse['tenant']
}

export interface RepaymentOrder {
  id: string
  order_id: string | null
  payment_id: string | null
  loan_id: string
  amount_paise: number
  currency: string
  status: string
  created_at: string | null
  key_id?: string
  is_test_mode?: boolean
  is_simulated?: boolean
  provider_confirmed?: boolean
  ledger_updated?: boolean
  message?: string
  idempotent_replay?: boolean
}

function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Accept': 'application/json'
  }
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('aura_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }
  return headers
}

export const api = {
  hasAccessToken(): boolean {
    return typeof window !== 'undefined' && Boolean(localStorage.getItem('aura_token'))
  },

  getSessionProfile(): ApiSessionProfile | null {
    if (typeof window === 'undefined') return null
    try {
      const profile = localStorage.getItem('aura_profile')
      return profile ? JSON.parse(profile) as ApiSessionProfile : null
    } catch {
      return null
    }
  },

  storeSession(session: ApiAuthResponse): void {
    localStorage.setItem('aura_token', session.access_token)
    localStorage.setItem('aura_profile', JSON.stringify({ user: session.user, tenant: session.tenant }))
  },

  async login(email: string, password: string): Promise<ApiAuthResponse> {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Unable to sign in')
    }
    return res.json()
  },

  async register(data: { email: string; password: string; full_name: string; organization_name?: string }): Promise<ApiAuthResponse> {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Unable to create your account')
    }
    return res.json()
  },

  // Cases
  async getCases(q?: string, status?: string): Promise<CaseItem[]> {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (status && status !== 'All') params.set('status', status)
    const res = await fetch(`${BASE_URL}/cases/?${params.toString()}`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load cases')
    return res.json()
  },

  async createCase(data: {
    customer_name: string
    requested_amount: number
    tenure_months: number
    purpose?: string
    product_type?: string
  }): Promise<CaseItem> {
    const res = await fetch(`${BASE_URL}/cases/`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to create case')
    }
    return res.json()
  },

  async getCaseDetail(caseId: string): Promise<{
    case: CaseItem
    evidence: EvidenceItem[]
    findings: ValidationFinding[]
    decisions: DecisionItem[]
  }> {
    const res = await fetch(`${BASE_URL}/cases/${caseId}`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load case details')
    return res.json()
  },

  async transitionCase(caseId: string, targetStatus: string, reason?: string): Promise<any> {
    const params = new URLSearchParams({ target_status: targetStatus })
    if (reason) params.set('reason', reason)
    const res = await fetch(`${BASE_URL}/cases/${caseId}/transition?${params.toString()}`, {
      method: 'POST',
      headers: getHeaders()
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Transition rejected by state machine')
    }
    return res.json()
  },

  // Evidence
  async getEvidence(caseId?: string): Promise<EvidenceItem[]> {
    const url = caseId ? `${BASE_URL}/evidence/?case_id=${caseId}` : `${BASE_URL}/evidence/`
    const res = await fetch(url, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load evidence')
    return res.json()
  },

  async uploadEvidence(file: File, caseId?: string): Promise<EvidenceItem> {
    const formData = new FormData()
    formData.append('file', file)
    if (caseId) formData.append('case_id', caseId)
    const res = await fetch(`${BASE_URL}/evidence/upload`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('aura_token')
          ? { Authorization: `Bearer ${localStorage.getItem('aura_token')}` }
          : {})
      },
      body: formData
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload failed')
    }
    return res.json()
  },

  // Validation
  async runValidation(caseId: string): Promise<{
    overall_status: string
    passed_rules: number
    failed_rules: number
    warning_rules: number
    findings: ValidationFinding[]
  }> {
    const res = await fetch(`${BASE_URL}/validation/run`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId })
    })
    if (!res.ok) throw new Error('Validation failed')
    return res.json()
  },

  // Decisions
  async recordDecision(data: {
    case_id: string
    outcome: string
    eligible_amount?: number
    interest_rate?: number
    rationale: string
  }): Promise<DecisionItem> {
    const res = await fetch(`${BASE_URL}/decisions/`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to record decision')
    }
    return res.json()
  },

  // Audit
  async getAuditLog(limit = 50, q?: string): Promise<AuditEventItem[]> {
    const params = new URLSearchParams({ limit: String(limit) })
    if (q) params.set('q', q)
    const res = await fetch(`${BASE_URL}/audit/?${params.toString()}`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load audit history')
    return res.json()
  },

  async verifyAuditIntegrity(): Promise<{
    total_events: number
    is_valid: boolean
    tampered_count: number
  }> {
    const res = await fetch(`${BASE_URL}/audit/verify`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to verify audit trail')
    return res.json()
  },

  // Analytics
  async getAnalytics(): Promise<AnalyticsDashboard> {
    const res = await fetch(`${BASE_URL}/analytics/dashboard`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load analytics')
    return res.json()
  },

  // Team
  async getTeam(): Promise<TeamMember[]> {
    const res = await fetch(`${BASE_URL}/team/`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load team')
    return res.json()
  },

  async inviteMember(data: { email: string; full_name: string; role: string }): Promise<TeamMember> {
    const res = await fetch(`${BASE_URL}/team/invite`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to invite team member')
    }
    return res.json()
  },

  // Billing
  async getBilling(): Promise<BillingSummary> {
    const res = await fetch(`${BASE_URL}/billing/summary`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load billing')
    return res.json()
  },

  // System
  async getSystemHealth(): Promise<{ status: string; database: string }> {
    const res = await fetch(`${BASE_URL}/system/health`, { headers: getHeaders() })
    if (!res.ok) throw new Error('System unavailable')
    return res.json()
  },

  // Integrations & Environment Settings
  async getIntegrations(): Promise<{ adapters: AdapterStatus[]; environment: string; production_enabled: boolean }> {
    const res = await fetch(`${BASE_URL}/integrations/`, { headers: getHeaders() })
    if (!res.ok) throw new Error('Failed to load integrations')
    return res.json()
  },

  async updateIntegrationMode(adapterName: string, mode: string): Promise<AdapterStatus> {
    const res = await fetch(`${BASE_URL}/integrations/${encodeURIComponent(adapterName)}/mode`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to switch adapter mode')
    }
    return res.json()
  },

  async simulateIntegrationFailure(adapterName: string, scenario?: string): Promise<AdapterStatus> {
    const res = await fetch(`${BASE_URL}/integrations/${encodeURIComponent(adapterName)}/simulate-failure`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenario || null })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to set failure scenario')
    }
    return res.json()
  },

  async testIntegrationConnection(adapterName: string): Promise<{ success: boolean; status: string; latency_ms: number; is_simulated?: boolean; message?: string; error?: string }> {
    const res = await fetch(`${BASE_URL}/integrations/${encodeURIComponent(adapterName)}/test-connection`, {
      method: 'POST',
      headers: getHeaders()
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Connection test failed')
    }
    return res.json()
  },

  // Gold Loan LOS / LMS Operations
  async calculateValuation(payload: {
    items: Array<{ item_type: string; gross_weight_mg: number; stone_deduction_mg?: number; purity_bps: number }>;
    ltv_scheme_pct?: number;
    credit_limit_paise?: number;
  }): Promise<ValuationResponse> {
    const res = await fetch(`${BASE_URL}/gold-loan/valuation/calculate`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Valuation failed')
    }
    return res.json()
  },

  async simulateDeviceReading(deviceId: string, grossWeightMg: number, purityBps: number): Promise<any> {
    const params = new URLSearchParams({
      device_id: deviceId,
      gross_weight_mg: String(grossWeightMg),
      purity_bps: String(purityBps)
    })
    const res = await fetch(`${BASE_URL}/gold-loan/assay/simulate-reading?${params.toString()}`, {
      method: 'POST',
      headers: getHeaders()
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Device reading failed')
    }
    return res.json()
  },

  async verifyDeviceReading(reading: any): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/assay/verify-reading`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(reading)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Reading verification failed')
    }
    return res.json()
  },

  async verifyPan(pan: string, customerName: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/kyc/verify-pan`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ pan, customer_name: customerName })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'PAN simulator request failed')
    }
    return res.json()
  },

  async verifyAadhaar(aadhaarNumber: string, otp: string, consentGiven: boolean): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/kyc/verify-aadhaar`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ aadhaar_number: aadhaarNumber, otp, consent_given: consentGiven })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Aadhaar simulator request failed')
    }
    return res.json()
  },

  async getRepaymentOrders(): Promise<RepaymentOrder[]> {
    const res = await fetch(`${BASE_URL}/gold-loan/repayments/orders`, { headers: getHeaders() })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to load repayment orders')
    }
    const data: { orders: RepaymentOrder[] } = await res.json()
    return data.orders
  },

  async createRepaymentOrder(loanId: string, amountPaise: number, idempotencyKey: string): Promise<RepaymentOrder> {
    const res = await fetch(`${BASE_URL}/gold-loan/repayments/create-order`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ loan_id: loanId, amount_paise: amountPaise, idempotency_key: idempotencyKey })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to create payment order')
    }
    return res.json()
  },

  async verifyRepaymentPayment(orderId: string, paymentId: string, signature: string): Promise<RepaymentOrder> {
    const res = await fetch(`${BASE_URL}/gold-loan/repayments/verify-payment`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: orderId, payment_id: paymentId, signature })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Unable to verify Razorpay payment')
    }
    return res.json()
  },

  async executeDisbursal(payload: {
    loan_id: string;
    amount_paise: number;
    beneficiary_account: string;
    beneficiary_ifsc: string;
    beneficiary_name: string;
    maker_id: string;
    checker_id: string;
    idempotency_key: string;
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/disbursals/execute`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Disbursal failed')
    }
    return res.json()
  },

  async sealVaultPacket(payload: {
    loan_id: string;
    custodian_1_id: string;
    custodian_2_id: string;
    vault_rack_id: string;
    item_count: number;
    net_weight_mg: number;
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/vault/seal`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Vault sealing failed')
    }
    return res.json()
  },

  async calculateAccrual(principalPaise: number, annualRatePct: number, days: number): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/servicing/accrue`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ principal_paise: principalPaise, annual_rate_pct: annualRatePct, days })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Interest accrual preview failed')
    }
    return res.json()
  },

  async allocateRepayment(payload: {
    payment_amount_paise: number;
    current_principal_paise: number;
    accrued_interest_paise: number;
    overdue_interest_paise?: number;
    penal_charges_paise?: number;
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/servicing/allocate-repayment`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to calculate repayment allocation')
    }
    return res.json()
  },

  async evaluateMtm(payload: {
    loan_id: string;
    total_outstanding_paise: number;
    net_gold_weight_mg: number;
    purity_bps?: number;
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/gold-loan/collections/evaluate-mtm`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Collateral revaluation preview failed')
    }
    return res.json()
  }
}
