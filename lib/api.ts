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
  }
}
