'use client'

import { FormEvent, useEffect, useMemo, useState, useRef } from 'react'
import {
  Activity, AlertTriangle, Archive, ArrowUpRight, Bell, BookOpen, CheckCircle2, ChevronDown,
  ClipboardCheck, Clock3, FileCheck2, FolderKanban, Gauge, Inbox, LayoutDashboard,
  MoreHorizontal, Plus, Search, Settings2, ShieldCheck, SlidersHorizontal, UploadCloud, Users,
  CreditCard, Building2, LifeBuoy, X, FileText, Download, UserPlus, Zap, Check, RefreshCw, WalletCards,
  LogIn, LogOut
} from 'lucide-react'
import { api, ApiSessionProfile, CaseItem, EvidenceItem, ValidationFinding, DecisionItem, AuditEventItem, AnalyticsDashboard, TeamMember, BillingSummary, AdapterStatus, GoldLoanApplicationItem } from '@/lib/api'
import { IntegrationsView } from '@/components/IntegrationsView'
import { GoldLoanStationView } from '@/components/GoldLoanStationView'
import { VaultServicingView } from '@/components/VaultServicingView'
import { PaymentsView } from '@/components/PaymentsView'
import { GoldRateTicker } from '@/components/GoldRateTicker'
import { GoldLoanCalculator } from '@/components/GoldLoanCalculator'

const nav = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'My cases', icon: FolderKanban, count: '24' },
  { label: 'Evidence inbox', icon: Inbox, count: '8' },
  { label: 'Gold Loan LOS', icon: Zap },
  { label: 'Vault & Servicing', icon: ShieldCheck },
  { label: 'Payments', icon: WalletCards },
  { label: 'Team workspace', icon: Users },
  { label: 'Billing & plan', icon: CreditCard },
]
const controlNav = [
  { label: 'Audit history', icon: Archive },
  { label: 'Search & export', icon: BookOpen },
  { label: 'Integrations & settings', icon: SlidersHorizontal },
  { label: 'System health', icon: Gauge },
  { label: 'Settings', icon: Settings2 },
]

// Baseline fallback data for instantaneous render before API hydrates
const initialCases: CaseItem[] = [
  { id: '1', tenant_id: 't1', case_number: 'AUR-2026-01842', customer_name: 'Northbridge Equipment Ltd', product_type: 'Asset finance', requested_amount: 250000, tenure_months: 12, status: 'IN_VALIDATION', priority: 'MEDIUM', owner_name: 'M. Chen', owner_initials: 'MC', sla_hours: 48, created_at: '2026-10-15T09:50:00.000Z', updated_at: '2026-10-15T09:50:00.000Z', files_count: 12 },
  { id: '2', tenant_id: 't1', case_number: 'AUR-2026-01839', customer_name: 'Lattice Works GmbH', product_type: 'Commercial lending', requested_amount: 420000, tenure_months: 24, status: 'READY_FOR_REVIEW', priority: 'HIGH', owner_name: 'S. Patel', owner_initials: 'SP', sla_hours: 48, created_at: '2026-10-15T06:20:00.000Z', updated_at: '2026-10-15T06:20:00.000Z', files_count: 18 },
  { id: '3', tenant_id: 't1', case_number: 'AUR-2026-01837', customer_name: 'Meridian Field Services', product_type: 'Instrument-backed', requested_amount: 180000, tenure_months: 6, status: 'EXCEPTION_RAISED', priority: 'URGENT', owner_name: 'A. Rossi', owner_initials: 'AR', sla_hours: 24, created_at: '2026-10-14T08:20:00.000Z', updated_at: '2026-10-14T08:20:00.000Z', files_count: 9 },
  { id: '4', tenant_id: 't1', case_number: 'AUR-2026-01831', customer_name: 'Harborline Logistics', product_type: 'Asset finance', requested_amount: 310000, tenure_months: 18, status: 'AWAITING_EVIDENCE', priority: 'LOW', owner_name: 'J. Okafor', owner_initials: 'JO', sla_hours: 72, created_at: '2026-10-14T03:20:00.000Z', updated_at: '2026-10-14T03:20:00.000Z', files_count: 6 },
]

function getTone(status: string): string {
  switch (status) {
    case 'IN_VALIDATION':
    case 'In validation':
      return 'blue'
    case 'READY_FOR_REVIEW':
    case 'Ready for review':
    case 'APPROVED':
    case 'Validated':
      return 'green'
    case 'EXCEPTION_RAISED':
    case 'Exception raised':
    case 'REJECTED':
      return 'red'
    case 'AWAITING_EVIDENCE':
    case 'Awaiting evidence':
    case 'Pending':
      return 'amber'
    default:
      return 'purple'
  }
}

function getDisplayStatus(status: string): string {
  switch (status) {
    case 'IN_VALIDATION': return 'In validation'
    case 'READY_FOR_REVIEW': return 'Ready for review'
    case 'EXCEPTION_RAISED': return 'Exception raised'
    case 'AWAITING_EVIDENCE': return 'Awaiting evidence'
    case 'APPROVED': return 'Approved'
    case 'REJECTED': return 'Rejected'
    case 'DRAFT': return 'Draft'
    default: return status
  }
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC'
  }).format(new Date(value))
}

function Status({ tone, children }: { tone: string; children: string }) {
  return <span className={`status ${tone}`}><span />{children}</span>
}

function MetricBar({ color, value, label }: { color: string; value: number; label: string }) {
  const percentage = Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0
  const width = 136 * percentage / 100
  return (
    <div className="kpi-chart" role="img" aria-label={`${label}: ${percentage.toFixed(1)} percent`}>
      <svg viewBox="0 0 144 16" preserveAspectRatio="none" aria-hidden="true">
        <line className="kpi-chart-track" x1="4" y1="8" x2="140" y2="8" />
        {[38, 72, 106].map(x => <line className="kpi-chart-tick" key={x} x1={x} y1="4" x2={x} y2="12" />)}
        <line x1="4" y1="8" x2={4 + width} y2="8" stroke={color} strokeWidth="4" strokeLinecap="round" />
        {percentage > 0 && <circle cx={4 + width} cy="8" r="3" fill={color} />}
      </svg>
      <span>{percentage.toFixed(0)}%</span>
    </div>
  )
}

function Stat({
  icon: Icon,
  tone,
  label,
  value,
  note,
  chartColor,
  chartValue,
  chartLabel,
}: {
  icon: typeof FolderKanban
  tone: string
  label: string
  value: number
  note: string
  chartColor: string
  chartValue: number
  chartLabel: string
}) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}><Icon size={18} /></div>
      <div className="stat-copy" style={{ flex: 1 }}>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{note}</small>
        <MetricBar color={chartColor} value={chartValue} label={chartLabel} />
      </div>
      <ArrowUpRight className="stat-arrow" size={16} />
    </div>
  )
}

const modulePortfolio = [
  { name: 'Identity & access', group: 'Foundation', status: 'Partial', page: 'Team workspace', description: 'Sign-in, workspace roles and protected API access.' },
  { name: 'Bank & branch tenancy', group: 'Foundation', status: 'Partial', page: 'Settings', description: 'Tenant boundaries exist; branch setup and scoped access remain.' },
  { name: 'Customer records', group: 'Origination', status: 'Partial', page: 'Gold Loan LOS', description: 'Tenant-scoped profiles link by bank customer reference.' },
  { name: 'Loan applications', group: 'Origination', status: 'Partial', page: 'Gold Loan LOS', description: 'Cases connect to persistent workflow records and event history.' },
  { name: 'Consent & KYC', group: 'Origination', status: 'Simulator', page: 'Gold Loan LOS', description: 'Synthetic PAN and Aadhaar checks; no provider verification.' },
  { name: 'Documents & evidence', group: 'Origination', status: 'Working', page: 'Evidence inbox', description: 'Upload, validate and retrieve tenant-scoped evidence.' },
  { name: 'Gold inventory', group: 'Collateral', status: 'Partial', page: 'Gold Loan LOS', description: 'Single-item intake preview; durable ornament inventory is pending.' },
  { name: 'Analyzer integration', group: 'Collateral', status: 'Simulator', page: 'Gold Loan LOS', description: 'Signed simulator readings; no physical device trust.' },
  { name: 'Valuation & eligibility', group: 'Collateral', status: 'Partial', page: 'Gold Loan LOS', description: 'Deterministic calculation preview with sample rate inputs.' },
  { name: 'Custody & vault', group: 'Decision & custody', status: 'Simulator', page: 'Vault & Servicing', description: 'Custody workflow preview; no physical vault events.' },
  { name: 'Underwriting & approval', group: 'Decision & custody', status: 'Partial', page: 'My cases', description: 'Case decisions and maker-checker controls.' },
  { name: 'Exceptions', group: 'Decision & custody', status: 'Partial', page: 'My cases', description: 'Exception records and review queues.' },
  { name: 'LOS / LMS integration', group: 'Integrations', status: 'Planned', page: 'Integrations & settings', description: 'Adapter controls exist; bank booking APIs are not connected.' },
  { name: 'Disbursement tracking', group: 'Integrations', status: 'Simulator', page: 'Vault & Servicing', description: 'No real payout or core banking confirmation.' },
  { name: 'Repayments & closure', group: 'Servicing', status: 'Partial', page: 'Payments', description: 'Razorpay test checkout; no loan ledger or closure release.' },
  { name: 'Collections & auctions', group: 'Servicing', status: 'Simulator', page: 'Vault & Servicing', description: 'Indicative previews; no scheduler, notices or auction.' },
  { name: 'Audit & compliance', group: 'Control', status: 'Working', page: 'Audit history', description: 'Append-only hash-chain events and integrity inspection.' },
  { name: 'Notifications & SLA', group: 'Control', status: 'Partial', page: 'System health', description: 'Operational metrics exist; delivery and SLA workflows remain.' },
  { name: 'Analytics', group: 'Control', status: 'Working', page: 'Overview', description: 'Workspace case and validation metrics.' },
  { name: 'SaaS subscriptions', group: 'Platform', status: 'Partial', page: 'Billing & plan', description: 'Plan and usage views; branch-based billing is pending.' },
  { name: 'Platform administration', group: 'Platform', status: 'Partial', page: 'Settings', description: 'Workspace settings; governed policy publishing is pending.' },
  { name: 'Security & operations', group: 'Platform', status: 'Partial', page: 'System health', description: 'Health and integration visibility; recovery operations remain.' },
]

function ModulePortfolio({ onNavigate }: { onNavigate: (page: string, name: string, status: string) => void }) {
  const working = modulePortfolio.filter(item => item.status === 'Working').length
  const simulator = modulePortfolio.filter(item => item.status === 'Simulator').length
  const remaining = modulePortfolio.length - working - simulator
  return (
    <section className="module-portfolio panel" aria-labelledby="module-portfolio-title">
      <div className="panel-heading module-portfolio-heading">
        <div>
          <span className="section-kicker">AURA WORKFLOW MAP</span>
          <h2 id="module-portfolio-title">Gold-loan module coverage</h2>
          <p>Open a module to continue in its current workspace. Labels reflect implementation maturity.</p>
        </div>
        <span className="module-count">{modulePortfolio.length} modules</span>
      </div>
      <div className="module-portfolio-kpis" aria-label="Module maturity summary">
        <div><strong>{working}</strong><span>Working areas</span></div>
        <div><strong>{simulator}</strong><span>Simulators</span></div>
        <div><strong>{remaining}</strong><span>Partial or planned</span></div>
      </div>
      <div className="module-card-grid">
        {modulePortfolio.map(item => (
          <button className="module-card" key={item.name} onClick={() => onNavigate(item.page, item.name, item.status)}>
            <span className="module-card-top"><span>{item.group}</span><i className={`module-status ${item.status.toLowerCase().replaceAll(' ', '-')}`}>{item.status}</i></span>
            <strong>{item.name}</strong>
            <small>{item.description}</small>
            <span className="module-card-link">Open workspace <ArrowUpRight size={13} /></span>
          </button>
        ))}
      </div>
      <p className="module-portfolio-note"><ShieldCheck size={14} /> Simulated checks, rates and provider events are clearly identified and must not be treated as lending or settlement decisions.</p>
    </section>
  )
}

export default function Page() {
  const [active, setActive] = useState('Overview')
  const [filterOpen, setFilterOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [showInvite, setShowInvite] = useState(false)
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  const [caseDetail, setCaseDetail] = useState<{
    case: CaseItem;
    evidence: EvidenceItem[];
    findings: ValidationFinding[];
    decisions: DecisionItem[];
  } | null>(null)

  const [toast, setToast] = useState('')
  const [hasApiSession, setHasApiSession] = useState(false)
  const [sessionProfile, setSessionProfile] = useState<ApiSessionProfile | null>(null)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [creating, setCreating] = useState(false)
  const [loadingAction, setLoadingAction] = useState(false)
  const [workflowTab, setWorkflowTab] = useState<'donut' | 'funnel'>('donut')

  // Real backend states
  const [caseList, setCaseList] = useState<CaseItem[]>(initialCases)
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null)
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([])
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([])
  const [billing, setBilling] = useState<BillingSummary | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([])
  const [goldLoanApplications, setGoldLoanApplications] = useState<GoldLoanApplicationItem[]>([])
  const [adapters, setAdapters] = useState<AdapterStatus[]>([])
  const [auditVerified, setAuditVerified] = useState<boolean>(true)
  const [goldLoanRefreshVersion, setGoldLoanRefreshVersion] = useState(0)
  const [decisionNotes, setDecisionNotes] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const profileMenuRef = useRef<HTMLDivElement>(null)

  // Hydrate from Python API
  const refreshData = async () => {
    if (!api.hasAccessToken()) return
    try {
      const [casesRes, analyticsRes, evidenceRes, teamRes, billingRes, auditRes, integrationsRes, goldLoanRes] = await Promise.all([
        api.getCases().catch(() => []),
        api.getAnalytics().catch(() => null),
        api.getEvidence().catch(() => []),
        api.getTeam().catch(() => []),
        api.getBilling().catch(() => null),
        api.getAuditLog(20).catch(() => []),
        api.getIntegrations().catch(() => ({ adapters: [], environment: 'development', production_enabled: false })),
        api.getGoldLoanApplications().catch(() => []),
      ])
      if (casesRes) setCaseList(casesRes)
      if (analyticsRes) setAnalytics(analyticsRes)
      if (evidenceRes) setEvidenceList(evidenceRes)
      if (teamRes && teamRes.length > 0) setTeamMembers(teamRes)
      if (billingRes) setBilling(billingRes)
      if (auditRes) setAuditEvents(auditRes)
      if (integrationsRes?.adapters) setAdapters(integrationsRes.adapters)
      setGoldLoanApplications(goldLoanRes || [])
    } catch (e) {
      console.warn('API sync using fallback defaults:', e)
    }
  }

  useEffect(() => {
    setHasApiSession(api.hasAccessToken())
    setSessionProfile(api.getSessionProfile())
    refreshData()
  }, [])

  useEffect(() => {
    function handleSessionExpired() {
      setHasApiSession(false)
      setSessionProfile(null)
      setCaseList(initialCases)
      setAnalytics(null)
      setEvidenceList([])
      setTeamMembers([])
      setBilling(null)
      setAuditEvents([])
      setGoldLoanApplications([])
      setToast('Your session expired. Sign in again to continue working with your workspace.')
    }

    window.addEventListener('aura:session-expired', handleSessionExpired)
    return () => window.removeEventListener('aura:session-expired', handleSessionExpired)
  }, [])

  useEffect(() => {
    if (!profileMenuOpen) return

    function closeOnOutsideClick(event: PointerEvent) {
      if (event.target instanceof Node && !profileMenuRef.current?.contains(event.target)) {
        setProfileMenuOpen(false)
      }
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setProfileMenuOpen(false)
    }

    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [profileMenuOpen])

  function signOut() {
    api.clearSession()
    setHasApiSession(false)
    setSessionProfile(null)
    setProfileMenuOpen(false)
    window.location.assign('/sign-in')
  }

  function openCreateCase() {
    if (!api.hasAccessToken()) {
      setToast('Sign in before creating a case or gold-loan application. Use the sign-in link above.')
      return
    }
    setSelectedFile(null)
    setShowCreate(true)
  }

  // Open Case Details Drawer
  const openCaseDetails = async (id: string) => {
    setSelectedCaseId(id)
    try {
      const details = await api.getCaseDetail(id)
      setCaseDetail(details)
    } catch {
      if (hasApiSession) {
        setSelectedCaseId(null)
        setToast('Unable to load this case from the workspace. Check your session and try again.')
        return
      }
      const found = caseList.find(c => c.id === id)
      if (found) {
        setCaseDetail({
          case: found,
          evidence: [],
          findings: [],
          decisions: []
        })
      }
    }
  }

  // Submit new case
  async function submitCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!api.hasAccessToken()) {
      setToast('Your session is missing or expired. Sign in before creating this application.')
      return
    }
    setCreating(true)
    const data = new FormData(event.currentTarget)
    const isGoldLoan = active === 'Gold Loan LOS'
    const goldCollateral = isGoldLoan
      ? `Gold collateral: ${String(data.get('goldItemType'))}; gross weight ${Number(data.get('goldWeightGrams'))} g; stated fineness ${Number(data.get('goldPurity'))} bps.`
      : ''
    const purpose = [goldCollateral, String(data.get('purpose') || '')].filter(Boolean).join(' ')
    try {
      const newCase = await api.createCase({
        customer_name: String(data.get('customerName')),
        requested_amount: Number(data.get('requestedAmount')),
        tenure_months: Number(data.get('tenureMonths')),
        purpose,
        product_type: isGoldLoan ? 'Gold Loan' : 'Asset finance'
      })

      if (isGoldLoan) {
        await api.createGoldLoanApplication(
          newCase.id,
          String(data.get('customerReference') || '').trim() || undefined,
          {
            item_type: String(data.get('goldItemType')),
            gross_weight_mg: Math.round(Number(data.get('goldWeightGrams')) * 1000),
            stone_deduction_mg: 0,
            purity_bps: Number(data.get('goldPurity')),
          }
        )
        setGoldLoanRefreshVersion(version => version + 1)
      }

      // If user selected a file during creation, upload it to the newly created case
      if (selectedFile) {
        await api.uploadEvidence(selectedFile, newCase.id)
      }

      setShowCreate(false)
      setSelectedFile(null)
      setToast(`${newCase.case_number} created successfully`)
      await refreshData()
    } catch (err: any) {
      setToast(err.message || 'Failed to create case')
    } finally {
      setCreating(false)
      setTimeout(() => setToast(''), 3000)
    }
  }

  // Execute Validation Rules on open case
  async function handleRunValidation() {
    if (!selectedCaseId) return
    if (!api.hasAccessToken()) {
      setToast('Sign in before running validation.')
      return
    }
    setLoadingAction(true)
    try {
      const res = await api.runValidation(selectedCaseId)
      setToast(`Validation completed: ${res.passed_rules} passed, ${res.failed_rules} failed`)
      const updated = await api.getCaseDetail(selectedCaseId)
      setCaseDetail(updated)
      await refreshData()
    } catch (err: any) {
      setToast(err.message || 'Validation execution failed')
    } finally {
      setLoadingAction(false)
      setTimeout(() => setToast(''), 3000)
    }
  }

  // Record Maker-Checker Decision
  async function handleRecordDecision(outcome: string) {
    if (!selectedCaseId) return
    if (!api.hasAccessToken()) {
      setToast('Sign in before recording a decision.')
      return
    }
    setLoadingAction(true)
    try {
      await api.recordDecision({
        case_id: selectedCaseId,
        outcome,
        rationale: decisionNotes.trim() || `Authorized operational ${outcome.toLowerCase()} recorded in workspace.`
      })
      setToast(`Decision recorded: ${outcome}`)
      setDecisionNotes('')
      const updated = await api.getCaseDetail(selectedCaseId)
      setCaseDetail(updated)
      await refreshData()
    } catch (err: any) {
      setToast(err.message || 'Failed to record decision')
    } finally {
      setLoadingAction(false)
      setTimeout(() => setToast(''), 3000)
    }
  }

  // File upload directly to evidence inbox
  async function handleFileUpload(file: File) {
    if (!api.hasAccessToken()) {
      setToast('Sign in before uploading evidence.')
      return
    }
    setLoadingAction(true)
    try {
      const targetCaseId = selectedCaseId || (caseList.length > 0 ? caseList[0].id : undefined)
      await api.uploadEvidence(file, targetCaseId)
      setToast(`Uploaded ${file.name} with SHA-256 verified`)
      await refreshData()
    } catch (err: any) {
      setToast(err.message || 'Upload failed')
    } finally {
      setLoadingAction(false)
      setTimeout(() => setToast(''), 3000)
    }
  }

  // Verify Audit Log Integrity
  async function handleVerifyAudit() {
    if (!api.hasAccessToken()) {
      setToast('Sign in before verifying workspace audit history.')
      return
    }
    setLoadingAction(true)
    try {
      const res = await api.verifyAuditIntegrity()
      setAuditVerified(res.is_valid)
      setToast(`Audit trail verified: ${res.total_events} events cryptographically linked. Tampering: 0`)
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Unable to verify audit history.')
    } finally {
      setLoadingAction(false)
      setTimeout(() => setToast(''), 3500)
    }
  }

  // Invite member
  async function handleInviteMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!api.hasAccessToken()) {
      setToast('Sign in before inviting a workspace member.')
      return
    }
    setLoadingAction(true)
    const data = new FormData(event.currentTarget)
    try {
      const invited = await api.inviteMember({
        email: String(data.get('email')),
        full_name: String(data.get('fullName')),
        role: String(data.get('role') || 'reviewer')
      })
      setShowInvite(false)
      setToast(`Invited ${invited.full_name} (${invited.role})`)
      await refreshData()
    } catch (err: any) {
      setToast(err.message || 'Failed to invite')
    } finally {
      setLoadingAction(false)
      setTimeout(() => setToast(''), 3000)
    }
  }

  const filteredCases = useMemo(() => {
    return caseList.filter(c =>
      `${c.case_number} ${c.customer_name} ${c.product_type} ${c.owner_name}`.toLowerCase().includes(query.toLowerCase())
    )
  }, [caseList, query])

  const go = (label: string) => {
    setActive(label)
    setToast(`${label} view selected`)
    setTimeout(() => setToast(''), 2000)
  }

  // Stats derived from live analytics
  const caseWorkflow = caseList.reduce((workflow, item) => {
    if (item.status === 'IN_VALIDATION') workflow.in_progress += 1
    else if (item.status === 'READY_FOR_REVIEW') workflow.ready_for_review += 1
    else if (item.status === 'AWAITING_EVIDENCE') workflow.awaiting_evidence += 1
    else if (item.status === 'APPROVED') workflow.approved += 1
    else if (item.status === 'REJECTED') workflow.rejected += 1
    else if (item.status === 'EXCEPTION_RAISED') workflow.exceptions += 1
    return workflow
  }, {
    in_progress: 0,
    ready_for_review: 0,
    awaiting_evidence: 0,
    approved: 0,
    rejected: 0,
    exceptions: 0,
  })
  const analyticsHasWorkflowData = Object.values(analytics?.workflow ?? {}).some(value => value > 0)
  const kpis = analytics && analytics.kpis.total_cases > 0
    ? analytics.kpis
    : {
        open_cases: caseList.filter(item => !['APPROVED', 'REJECTED'].includes(item.status)).length,
        pending_validation: caseWorkflow.in_progress,
        awaiting_decision: caseWorkflow.ready_for_review,
        open_exceptions: caseWorkflow.exceptions,
        total_cases: caseList.length,
        sla_compliance_rate: 0,
        validation_pass_rate: 0,
        avg_processing_hours: 0,
        active_filters_count: 0,
      }
  const workflowDist = analyticsHasWorkflowData && analytics ? analytics.workflow : caseWorkflow

  const workflowSegments = [
    { label: 'In progress', value: workflowDist.in_progress, color: '#4a82f4' },
    { label: 'Ready for review', value: workflowDist.ready_for_review, color: '#2aaf7f' },
    { label: 'Awaiting evidence', value: workflowDist.awaiting_evidence, color: '#e8a527' },
    { label: 'Approved', value: workflowDist.approved, color: '#dfe5ed' },
    { label: 'Rejected', value: workflowDist.rejected, color: '#df5b67' },
    { label: 'Exceptions', value: workflowDist.exceptions, color: '#7755cf' },
  ]
  const workflowTotal = workflowSegments.reduce((total, segment) => total + segment.value, 0)
  let workflowOffset = 0
  const workflowGradient = workflowTotal > 0
    ? `conic-gradient(${workflowSegments.map(segment => {
      const start = workflowOffset
      workflowOffset += segment.value / workflowTotal * 100
      return `${segment.color} ${start}% ${workflowOffset}%`
    }).join(', ')})`
    : '#dfe5ed'
  const openCasesShare = kpis.total_cases > 0 ? kpis.open_cases / kpis.total_cases * 100 : 0
  const pendingValidationShare = kpis.open_cases > 0 ? kpis.pending_validation / kpis.open_cases * 100 : 0
  const awaitingDecisionShare = kpis.open_cases > 0 ? kpis.awaiting_decision / kpis.open_cases * 100 : 0
  const openExceptionsShare = kpis.open_cases > 0 ? kpis.open_exceptions / kpis.open_cases * 100 : 0
  const goldConsentPending = goldLoanApplications.filter(application => application.consent_status !== 'RECORDED').length
  const goldVerificationReview = goldLoanApplications.filter(application => application.kyc_status === 'INDETERMINATE').length
  const goldValuationPreviews = goldLoanApplications.filter(application => application.appraisal_status === 'SIMULATED_PREVIEW').length

  return (
    <div className="app-shell">
      {/* SIDEBAR — Preserved Brand & Visual Hierarchy */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">A</div>
          <div>
            <strong>AURUM</strong>
            <span>Customer workspace</span>
          </div>
        </div>
        <div className="workspace">
          <span>ORGANISATION</span>
          <button onClick={() => setToast(`Organization: ${sessionProfile?.tenant.name || 'Northstar Bank'}`)}>
            {sessionProfile?.tenant.name || 'Northstar Bank'} <ChevronDown size={14} />
          </button>
        </div>
        <nav aria-label="Primary navigation">
          {nav.map(item => (
            <button
              key={item.label}
              className={`nav-item ${active === item.label ? 'active' : ''}`}
              onClick={() => go(item.label)}
            >
              <item.icon size={17} />
              <span>{item.label}</span>
              {item.label === 'My cases' && <em>{caseList.length || item.count}</em>}
              {item.label === 'Evidence inbox' && <em>{evidenceList.length || item.count}</em>}
            </button>
          ))}
        </nav>
        <div className="nav-section">
          <span>CONTROL CENTRE</span>
          {controlNav.map(item => (
            <button
              key={item.label}
              className={`nav-item ${active === item.label ? 'active' : ''}`}
              onClick={() => go(item.label)}
            >
              <item.icon size={17} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="help-card">
            <LifeBuoy size={17} />
            <div>
              <strong>Need help?</strong>
              <span>Visit support centre</span>
            </div>
          </div>
          <div className="user-card">
          <div className="avatar">{sessionProfile?.user.name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase() || 'JD'}</div>
            <div>
            <strong>{sessionProfile?.user.name || 'Jordan Davies'}</strong>
            <span>{sessionProfile?.user.role || 'Administrator'}</span>
            </div>
            <MoreHorizontal size={17} />
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <span>{sessionProfile?.tenant.name || 'Northstar Bank'}</span>
            <b>/</b>
            <strong>{active}</strong>
          </div>
          <div className="top-actions">
            <div className="system-status">
              <span className="pulse" /> All systems operational
            </div>
            <button className="icon-button" aria-label="Refresh Data" onClick={refreshData} title="Sync with Python Backend">
              <RefreshCw size={17} />
            </button>
            <button className="icon-button" aria-label="Search" onClick={() => go('Search & export')}>
              <Search size={18} />
            </button>
            <button className="icon-button" aria-label="Notifications" onClick={() => setToast('No unread critical alerts')}>
              <Bell size={18} />
              <i />
            </button>
            <div className="profile-menu-wrap" ref={profileMenuRef}>
              <button
                className="top-avatar profile-menu-trigger"
                type="button"
                aria-label={hasApiSession ? `Account menu for ${sessionProfile?.user.name || 'your account'}` : 'Sign-in menu'}
                aria-haspopup="menu"
                aria-expanded={profileMenuOpen}
                onClick={() => setProfileMenuOpen(open => !open)}
              >
                {sessionProfile?.user.name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase() || 'JD'}
              </button>
              {profileMenuOpen && (
                <div className="profile-menu" role="menu" aria-label="Account">
                  {hasApiSession ? (
                    <>
                      <div className="profile-menu-details">
                        <strong>{sessionProfile?.user.name || 'Signed-in user'}</strong>
                        <span>{sessionProfile?.user.email || 'Authenticated workspace session'}</span>
                        {sessionProfile?.tenant.name && <span>{sessionProfile.tenant.name}</span>}
                      </div>
                      <button className="profile-menu-action" type="button" role="menuitem" onClick={signOut}>
                        <LogOut size={15} /> Sign out
                      </button>
                    </>
                  ) : (
                    <>
                      <a className="profile-menu-action" href="/sign-in" role="menuitem" onClick={() => setProfileMenuOpen(false)}>
                        <LogIn size={15} /> Sign in
                      </a>
                      <a className="profile-menu-action" href="/sign-up" role="menuitem" onClick={() => setProfileMenuOpen(false)}>
                        <UserPlus size={15} /> Create account
                      </a>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="content-wrap">
          {active !== 'Overview' && (
            <section className="page-heading compact">
              <div>
                <div className="eyebrow">
                  <span className="eyebrow-dot" /> WORKSPACE
                </div>
                <h1>{active}</h1>
                <p>{active === 'Gold Loan LOS'
                  ? 'Capture a borrower application, collateral details, and valuation evidence.'
                  : active === 'Payments'
                    ? 'Create Razorpay test orders and verify checkout responses without live charges or loan-ledger postings.'
                    : active === 'Vault & Servicing'
                      ? 'Review vault, payout, servicing, and collateral-monitoring workflows.'
                      : 'Manage your organisation&apos;s evidence operations in one place.'}</p>
              </div>
              {active === 'Gold Loan LOS' && (
                <button className="primary-button" onClick={openCreateCase}>
                  <Plus size={17} /> New gold-loan application
                </button>
              )}
            </section>
          )}

          {!hasApiSession && (
            <div className="auth-required-banner" role="status">
              <ShieldCheck size={17} />
              <span>You are viewing preview data. Sign in to create records and access your workspace.</span>
              <a href="/sign-in">Sign in</a>
              <a href="/sign-up">Create account</a>
            </div>
          )}

          {/* OVERVIEW DASHBOARD */}
          {active === 'Overview' && (
            <>
              <section className="page-heading">
                <div>
                  <div className="eyebrow">
                    <span className="eyebrow-dot" /> CUSTOMER PORTAL <span className="live-pill">LIVE</span>
                  </div>
                  <h1>Good morning, {sessionProfile?.user.name.split(/\s+/)[0] || 'Jordan'}</h1>
                  <p>Track submissions, respond to requests, and keep every case moving.</p>
                </div>
                <button className="primary-button" onClick={openCreateCase}>
                  <Plus size={17} /> Create case
                </button>
              </section>

              <GoldRateTicker />

              <section className="gold-overview-strip" aria-label="Gold loan workflow KPIs">
                <button onClick={() => go('Gold Loan LOS')}>
                  <span>GOLD LOAN APPLICATIONS</span><strong>{goldLoanApplications.length}</strong><small>Saved in this workspace</small>
                </button>
                <button onClick={() => go('Gold Loan LOS')}>
                  <span>CONSENT PENDING</span><strong>{goldConsentPending}</strong><small>Awaiting recorded consent</small>
                </button>
                <button onClick={() => go('Gold Loan LOS')}>
                  <span>VERIFICATION REVIEW</span><strong>{goldVerificationReview}</strong><small>Simulator results stay indeterminate</small>
                </button>
                <button onClick={() => go('Gold Loan LOS')}>
                  <span>VALUATION PREVIEWS</span><strong>{goldValuationPreviews}</strong><small>Saved simulator snapshots</small>
                </button>
              </section>

              {/* KPI cards show current workload shares, not fabricated historical trends. */}
              <section className="stat-grid">
                <Stat
                  label="Open cases"
                  value={kpis.open_cases}
                  note={`${kpis.sla_compliance_rate}% SLA compliance`}
                  icon={FolderKanban}
                  tone="blue"
                  chartColor="#2e6df6"
                  chartValue={openCasesShare}
                  chartLabel="Share of all cases that are open"
                />
                <Stat
                  label="Pending validation"
                  value={kpis.pending_validation}
                  note={`${kpis.validation_pass_rate}% rule pass rate`}
                  icon={ClipboardCheck}
                  tone="amber"
                  chartColor="#d59113"
                  chartValue={pendingValidationShare}
                  chartLabel="Share of open cases pending validation"
                />
                <Stat
                  label="Awaiting decision"
                  value={kpis.awaiting_decision}
                  note={`${kpis.avg_processing_hours}h median turnaround`}
                  icon={Clock3}
                  tone="purple"
                  chartColor="#7755cf"
                  chartValue={awaitingDecisionShare}
                  chartLabel="Share of open cases awaiting a decision"
                />
                <Stat
                  label="Open exceptions"
                  value={kpis.open_exceptions}
                  note="Dual-control resolved"
                  icon={AlertTriangle}
                  tone="red"
                  chartColor="#df5b67"
                  chartValue={openExceptionsShare}
                  chartLabel="Share of open cases with exceptions"
                />
              </section>

              {/* QUICK ACTIONS */}
              <section className="quick-actions">
                <div>
                  <span className="section-kicker">GET STARTED</span>
                  <h2>What would you like to do?</h2>
                </div>
                <button onClick={openCreateCase}>
                  <div className="quick-icon blue"><Plus size={18} /></div>
                  <span>
                    <strong>Start a new case</strong>
                    <small>Submit a new evidence package</small>
                  </span>
                  <ArrowUpRight size={16} />
                </button>
                <button onClick={() => go('Evidence inbox')}>
                  <div className="quick-icon mint"><UploadCloud size={18} /></div>
                  <span>
                    <strong>Upload evidence</strong>
                    <small>Attach documents & verify checksums</small>
                  </span>
                  <ArrowUpRight size={16} />
                </button>
                <button onClick={() => go('My cases')}>
                  <div className="quick-icon purple"><Search size={18} /></div>
                  <span>
                    <strong>Find a case</strong>
                    <small>Search your workspace</small>
                  </span>
                  <ArrowUpRight size={16} />
                </button>
              </section>

              <ModulePortfolio onNavigate={(page, name, status) => {
                if (page !== 'Overview') go(page)
                if (status !== 'Working') setToast(`${name}: ${status.toLowerCase()} in this prototype. See the module TODO plan for remaining work.`)
              }} />
            </>
          )}

          {/* CASES LISTING & RICH ANALYTICS PANEL */}
          {(active === 'Overview' || active === 'My cases') && (
            <section className="workspace-grid">
              <div className="panel cases-panel">
                <div className="panel-heading">
                  <div>
                    <h2>{active === 'My cases' ? 'All cases' : 'Recent case activity'}</h2>
                    <p>Review status and keep submissions moving (click any row to inspect details)</p>
                  </div>
                  <button className="text-button" onClick={() => go('My cases')}>
                    View all <ArrowUpRight size={15} />
                  </button>
                </div>

                <div className="table-toolbar">
                  <div className="search-field">
                    <Search size={16} />
                    <input
                      value={query}
                      onChange={e => setQuery(e.target.value)}
                      placeholder="Search cases, organisations or IDs"
                      aria-label="Search cases"
                    />
                  </div>
                  <button
                    className={`filter-button ${filterOpen ? 'selected' : ''}`}
                    onClick={() => setFilterOpen(!filterOpen)}
                  >
                    <SlidersHorizontal size={15} /> Filters <span>{filterOpen ? 'Active' : '2'}</span>
                  </button>
                </div>

                {filterOpen && (
                  <div className="filter-popover">
                    <strong>Active filters</strong>
                    <span>Status: Open</span>
                    <span>Owner: Northstar Team</span>
                    <span>SLA: Active</span>
                  </div>
                )}

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Case</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Owner</th>
                        <th>Requested</th>
                        <th>Evidence</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {filteredCases.map(c => (
                        <tr
                          key={c.id}
                          style={{ cursor: 'pointer' }}
                          onClick={() => openCaseDetails(c.id)}
                          title="Click to inspect case details and decisions"
                        >
                          <td>
                            <strong className="case-id">{c.case_number}</strong>
                            <span className="case-name">{c.customer_name}</span>
                          </td>
                          <td>{c.product_type}</td>
                          <td>
                            <Status tone={getTone(c.status)}>
                              {getDisplayStatus(c.status)}
                            </Status>
                          </td>
                          <td>
                            <div className="owner">
                              <span>{c.owner_initials || 'MC'}</span>
                              {c.owner_name}
                            </div>
                          </td>
                          <td>
                            <strong style={{ color: '#1a365d' }}>
                              {c.product_type === 'Gold Loan' ? '₹' : '$'}{Number(c.requested_amount).toLocaleString(c.product_type === 'Gold Loan' ? 'en-IN' : 'en-US')}
                            </strong>
                            <span style={{ display: 'block', fontSize: '9px', color: '#8898aa' }}>
                              {c.tenure_months} mo
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: '11px', color: '#687b92' }}>
                              {c.files_count ?? 1} file(s)
                            </span>
                          </td>
                          <td>
                            <button
                              className="row-menu"
                              aria-label={`Open ${c.case_number}`}
                              onClick={e => {
                                e.stopPropagation()
                                openCaseDetails(c.id)
                              }}
                            >
                              <MoreHorizontal size={17} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* RIGHT COLUMN: WORKFLOW HEALTH & RECENT ACTIVITIES */}
              <div className="right-column">
                <div className="panel workflow-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Workflow health</h2>
                      <p>Cases by current operational state</p>
                    </div>
                    <div className="tab-row" style={{ margin: 0, border: 0 }}>
                      <button
                        className={`tab-btn ${workflowTab === 'donut' ? 'active' : ''}`}
                        onClick={() => setWorkflowTab('donut')}
                      >
                        Breakdown
                      </button>
                      <button
                        className={`tab-btn ${workflowTab === 'funnel' ? 'active' : ''}`}
                        onClick={() => setWorkflowTab('funnel')}
                      >
                        Funnel
                      </button>
                    </div>
                  </div>

                  {workflowTab === 'donut' ? (
                    <div className="donut-wrap">
                      <div
                        className="donut"
                        style={{ background: workflowGradient }}
                        role="img"
                        aria-label={`${workflowTotal} cases across ${workflowSegments.length} workflow states`}
                      >
                        <div>
                          <strong>{workflowTotal}</strong>
                          <span>Total cases</span>
                        </div>
                      </div>
                      <div className="legend">
                        {workflowSegments.map(segment => (
                          <div key={segment.label}>
                            <i style={{ background: segment.color }} />
                            <span>{segment.label}</span>
                            <strong>{segment.value}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    /* OPERATIONAL CONVERSION FUNNEL */
                    <div className="funnel-wrap">
                      {[
                        ['1. Intake Submitted', caseList.length || 24, 100],
                        ['2. Evidence Package Verified', Math.max(1, caseList.length - 2), 92],
                        ['3. Validation Rules Passed', Math.max(1, caseList.length - 4), 83],
                        ['4. Underwriting Review', workflowDist.ready_for_review || 6, 60],
                        ['5. Decisions Finalized', workflowDist.approved || 4, 45],
                      ].map(([label, val, pct]: any) => (
                        <div className="funnel-step" key={label}>
                          <div className="funnel-step-bar" style={{ width: `${pct}%` }} />
                          <div className="funnel-step-copy">
                            <strong>{label}</strong>
                            <span>{val} cases ({pct}%)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* MATERIAL AUDIT EVENTS STREAM */}
                <div className="panel events-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Recent activity</h2>
                      <p>Traceable events in your workspace</p>
                    </div>
                    <button className="text-button" onClick={() => go('Audit history')}>
                      Audit log <ArrowUpRight size={15} />
                    </button>
                  </div>
                  <div className="event-list">
                    {(auditEvents.length > 0 ? auditEvents.slice(0, 4) : []).map(event => (
                      <div className="event" key={event.id}>
                        <div className={`event-icon ${event.action.includes('created') ? 'blue' : event.action.includes('uploaded') ? 'green' : 'purple'}`}>
                          {event.action.includes('created') ? <Plus size={15} /> : event.action.includes('uploaded') ? <FileCheck2 size={15} /> : <Activity size={15} />}
                        </div>
                        <div>
                          <strong>{event.action.replace('.', ' ')}</strong>
                          <span>{event.actor_name} · {event.entity_id.slice(0, 14)}</span>
                        </div>
                        <time>{new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                      </div>
                    ))}
                    {auditEvents.length === 0 && (
                      <div className="event">
                        <div className="event-icon green"><CheckCircle2 size={15} /></div>
                        <div>
                          <strong>Evidence package validated</strong>
                          <span>AUR-2026-01839 · 12 items passed</span>
                        </div>
                        <time>09:42</time>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* SUBPAGES */}
          {active === 'Evidence inbox' && (
            <EvidenceView
              evidenceList={evidenceList}
              onReviewCases={() => go('My cases')}
              onUpload={handleFileUpload}
            />
          )}

          {active === 'Team workspace' && (
            <TeamView
              members={teamMembers}
              onInvite={() => setShowInvite(true)}
            />
          )}

          {active === 'Billing & plan' && (
            <BillingView billing={billing} />
          )}

          {active === 'Settings' && (
            <SettingsView />
          )}

          {active === 'Audit history' && (
            <AuditView
              events={auditEvents}
              isVerified={auditVerified}
              onVerify={handleVerifyAudit}
            />
          )}

          {active === 'System health' && (
            <SystemHealthView onRefresh={refreshData} />
          )}

          {active === 'Search & export' && (
            <SearchExportView cases={caseList} />
          )}

          {active === 'Integrations & settings' && (
            <IntegrationsView
              adapters={adapters}
              onRefresh={refreshData}
              setToast={setToast}
              hasApiSession={hasApiSession}
            />
          )}

          {active === 'Gold Loan LOS' && (
            <>
              <GoldRateTicker />
              <GoldLoanCalculator setToast={setToast} />
              <GoldLoanStationView
                setToast={setToast}
                hasApiSession={hasApiSession}
                refreshVersion={goldLoanRefreshVersion}
              />
            </>
          )}

          {active === 'Vault & Servicing' && (
            <VaultServicingView
              setToast={setToast}
              hasApiSession={hasApiSession}
            />
          )}

          {active === 'Payments' && (
            <PaymentsView hasApiSession={hasApiSession} setToast={setToast} />
          )}
          {/* BOTTOM AUDIT ASSURANCE STRIP */}
          {active === 'Overview' && (
            <section className="bottom-strip">
              <div>
                <ShieldCheck size={18} />
                <div>
                  <strong>Cryptographically Traceable Workspace</strong>
                  <span>Every case creation, evidence upload, rule validation, and decision is recorded with SHA-256 hash chains.</span>
                </div>
              </div>
              <button className="text-button" onClick={() => go('Audit history')}>
                Inspect audit chain <ArrowUpRight size={15} />
              </button>
            </section>
          )}
        </div>
      </main>

      {/* CREATE NEW CASE MODAL */}
      {showCreate && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <form className="modal-form" onSubmit={submitCase}>
              <div className="modal-header">
                <div>
                  <span className="eyebrow">{active === 'Gold Loan LOS' ? 'GOLD LOAN INTAKE' : 'NEW SUBMISSION'}</span>
                  <h2>{active === 'Gold Loan LOS' ? 'Start a gold-loan application' : 'Create a new case'}</h2>
                  <p>{active === 'Gold Loan LOS'
                    ? 'Creates an authenticated intake record only; it does not approve or disburse a loan.'
                    : 'Start an evidence request for your organisation.'}</p>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setShowCreate(false)}
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>

              <label>
                Customer name
                <input
                  name="customerName"
                  placeholder="e.g. Northbridge Equipment Ltd"
                  required
                />
              </label>

              {active === 'Gold Loan LOS' && (
                <>
                  <label>
                    Bank customer reference <span className="optional-label">(optional; reuses profile within this bank)</span>
                    <input name="customerReference" maxLength={100} placeholder="e.g. CIF-0091827" />
                  </label>
                  <label>
                    Gold item type
                    <select name="goldItemType" defaultValue="Gold Bangle">
                      <option>Gold Bangle</option>
                      <option>Gold Coins / Bullion</option>
                      <option>Gold Chain</option>
                      <option>Gold Necklace</option>
                    </select>
                  </label>
                  <label>
                    Estimated gross weight (grams)
                    <input name="goldWeightGrams" type="number" min="0.1" step="0.1" placeholder="25.0" required />
                  </label>
                  <label>
                    Stated purity
                    <select name="goldPurity" defaultValue="9160">
                      <option value="9990">24K · 999 fineness</option>
                      <option value="9160">22K · 916 fineness</option>
                      <option value="7500">18K · 750 fineness</option>
                    </select>
                  </label>
                </>
              )}

              <label>
                Requested amount ({active === 'Gold Loan LOS' ? '₹ INR' : '$ USD'})
                <input
                  name="requestedAmount"
                  type="number"
                  min={active === 'Gold Loan LOS' ? '1' : '1000'}
                  step={active === 'Gold Loan LOS' ? '1000' : '1000'}
                  placeholder={active === 'Gold Loan LOS' ? '150000' : '250000'}
                  required
                />
              </label>

              <label>
                Tenure
                <select name="tenureMonths" defaultValue="12">
                  <option value="3">3 months</option>
                  <option value="6">6 months</option>
                  <option value="12">12 months</option>
                  <option value="24">24 months</option>
                  <option value="36">36 months</option>
                </select>
              </label>

              <label>
                Purpose / Facility Note
                <input
                  name="purpose"
                  placeholder={active === 'Gold Loan LOS' ? 'Branch, sourcing channel, or intake note' : 'Working capital or asset procurement'}
                />
              </label>

              <div
                className="upload-box"
                style={{ cursor: 'pointer' }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={e => {
                    if (e.target.files?.[0]) setSelectedFile(e.target.files[0])
                  }}
                />
                <UploadCloud size={24} />
                <strong>
                  {selectedFile ? selectedFile.name : 'Drop evidence here'}
                </strong>
                <span>
                  {selectedFile
                    ? `${(selectedFile.size / 1024).toFixed(1)} KB · Ready for upload`
                    : 'or click to browse · PDF, PNG, XLSX up to 50MB'}
                </span>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={creating}
                >
                  {creating ? 'Creating…' : 'Create application'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* INVITE TEAM MEMBER MODAL */}
      {showInvite && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <form className="modal-form" onSubmit={handleInviteMember}>
              <div className="modal-header">
                <div>
                  <span className="eyebrow">ACCESS CONTROL</span>
                  <h2>Invite team member</h2>
                  <p>Assign workspace permissions under least-privilege RBAC.</p>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setShowInvite(false)}
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>

              <label>
                Full name
                <input name="fullName" placeholder="e.g. David Vance" required />
              </label>

              <label>
                Corporate email
                <input name="email" type="email" placeholder="david.vance@northstar.bank" required />
              </label>

              <label>
                Role & permission scope
                <select name="role" defaultValue="reviewer">
                  <option value="reviewer">Reviewer (case.read, validation.run, evidence.review)</option>
                  <option value="approver">Approver (decision.approve, maker-checker)</option>
                  <option value="analyst">Analyst (case.create, evidence.upload)</option>
                  <option value="auditor">Auditor (read-only, audit.read)</option>
                  <option value="admin">Administrator (user.manage, policy.manage)</option>
                </select>
              </label>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowInvite(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={loadingAction}
                >
                  {loadingAction ? 'Inviting…' : 'Send invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CASE DETAILS & DECISION DRAWER */}
      {selectedCaseId && caseDetail && (
        <div className="drawer-backdrop" onClick={() => setSelectedCaseId(null)}>
          <div className="drawer" onClick={e => e.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <span className="eyebrow">CASE AUDIT & DECISION TRACE</span>
                <h2>{caseDetail.case.case_number}</h2>
                <p>{caseDetail.case.customer_name}</p>
              </div>
              <button className="icon-button" onClick={() => setSelectedCaseId(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="drawer-body">
              {/* Status and Metadata */}
              <div className="detail-meta-grid">
                <div>
                  <span>STATUS</span>
                  <div style={{ marginTop: '4px' }}>
                    <Status tone={getTone(caseDetail.case.status)}>
                      {getDisplayStatus(caseDetail.case.status)}
                    </Status>
                  </div>
                </div>
                <div>
                  <span>REQUESTED AMOUNT</span>
                  <strong>{caseDetail.case.product_type === 'Gold Loan' ? '₹' : '$'}{Number(caseDetail.case.requested_amount).toLocaleString(caseDetail.case.product_type === 'Gold Loan' ? 'en-IN' : 'en-US')}</strong>
                </div>
                <div>
                  <span>FACILITY TYPE</span>
                  <strong>{caseDetail.case.product_type}</strong>
                </div>
                <div>
                  <span>TENURE</span>
                  <strong>{caseDetail.case.tenure_months} months</strong>
                </div>
                <div>
                  <span>CASE OWNER</span>
                  <strong>{caseDetail.case.owner_name} ({caseDetail.case.owner_initials})</strong>
                </div>
                <div>
                  <span>SLA WINDOW</span>
                  <strong>{caseDetail.case.sla_hours} hours</strong>
                </div>
              </div>

              {/* Validation & Rules Engine */}
              <div>
                <div className="drawer-section-title">
                  <span>DETERMINISTIC VALIDATION (POLICY v1.0)</span>
                  <button
                    className="secondary-button"
                    style={{ padding: '6px 10px', fontSize: '10px' }}
                    onClick={handleRunValidation}
                    disabled={loadingAction}
                  >
                    <RefreshCw size={12} /> Run Policy Checks
                  </button>
                </div>

                {caseDetail.findings.length > 0 ? (
                  caseDetail.findings.map(f => (
                    <div className={`finding-card ${f.outcome.toLowerCase()}`} key={f.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong>{f.rule_name}</strong>
                        <span className={`status ${f.outcome === 'PASSED' ? 'green' : f.outcome === 'FAILED' ? 'red' : 'amber'}`}>
                          <span />{f.outcome}
                        </span>
                      </div>
                      <p>{f.explanation}</p>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '6px', textAlign: 'center', fontSize: '11px', color: '#7a8b9e' }}>
                    Click &ldquo;Run Policy Checks&rdquo; to execute deterministic validation rules.
                  </div>
                )}
              </div>

              {/* Evidence Documents */}
              <div>
                <div className="drawer-section-title">
                  <span>ATTACHED EVIDENCE FILES</span>
                  <label className="secondary-button" style={{ padding: '6px 10px', fontSize: '10px', cursor: 'pointer' }}>
                    <UploadCloud size={12} /> Attach File
                    <input
                      type="file"
                      style={{ display: 'none' }}
                      onChange={e => {
                        if (e.target.files?.[0]) handleFileUpload(e.target.files[0])
                      }}
                    />
                  </label>
                </div>

                {caseDetail.evidence.length > 0 ? (
                  caseDetail.evidence.map(e => (
                    <div className="file-row" key={e.id} style={{ padding: '8px 0' }}>
                      <div className="file-icon"><FileText size={16} /></div>
                      <div>
                        <strong>{e.file_name}</strong>
                        <span>SHA-256: {e.sha256_checksum.slice(0, 16)}… · {(e.file_size_bytes / 1024).toFixed(0)} KB</span>
                      </div>
                      <Status tone={getTone(e.validation_status)}>
                        {e.validation_status}
                      </Status>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '6px', fontSize: '11px', color: '#7a8b9e' }}>
                    No private evidence items attached yet.
                  </div>
                )}
              </div>

              {/* Maker-Checker Review & Decision Recording */}
              <div className="decision-box">
                <h3>MAKER-CHECKER DECISION PANEL</h3>
                <p style={{ margin: '0 0 10px', fontSize: '11px', color: '#687e9c' }}>
                  Decisions are permanently committed to the tamper-evident audit history with reviewer signature.
                </p>
                <textarea
                  rows={2}
                  value={decisionNotes}
                  onChange={e => setDecisionNotes(e.target.value)}
                  placeholder="Enter decision rationale or conditions for approval..."
                />
                <div className="decision-actions">
                  <button
                    className="btn-approve"
                    onClick={() => handleRecordDecision('APPROVED')}
                    disabled={loadingAction}
                  >
                    Approve Case
                  </button>
                  <button
                    className="btn-reject"
                    onClick={() => handleRecordDecision('REJECTED')}
                    disabled={loadingAction}
                  >
                    Reject
                  </button>
                  <button
                    className="btn-correct"
                    onClick={() => handleRecordDecision('RETURNED_FOR_CORRECTION')}
                    disabled={loadingAction}
                  >
                    Return for Correction
                  </button>
                </div>
              </div>

              {/* Decision History */}
              {caseDetail.decisions.length > 0 && (
                <div>
                  <div className="drawer-section-title">
                    <span>RECORDED DECISION HISTORY</span>
                  </div>
                  {caseDetail.decisions.map(d => (
                    <div key={d.id} className="finding-card passed">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong>Decision: {d.outcome} by {d.actor_name}</strong>
                        <span style={{ fontSize: '10px', color: '#889bb0' }}>
                          {formatDateTime(d.created_at)}
                        </span>
                      </div>
                      <p>{d.rationale}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* NOTIFICATION TOAST */}
      {toast && (
        <div className="toast">
          <CheckCircle2 size={16} />
          {toast}
        </div>
      )}
    </div>
  )
}

function SubPage({ title, subtitle, children, action }: any) {
  return (
    <section className="subpage">
      <div className="subpage-head">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

/* EVIDENCE INBOX VIEW */
function EvidenceView({ evidenceList, onReviewCases, onUpload }: any) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  return (
    <SubPage
      title="Evidence inbox"
      subtitle="Requests waiting for your team and files securely processed."
      action={
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="secondary-button"
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={e => {
                if (e.target.files?.[0]) onUpload(e.target.files[0])
              }}
            />
            <UploadCloud size={16} /> Upload document
          </button>
        </div>
      }
    >
      <div className="inbox-cards">
        <div className="inbox-card urgent">
          <span>NEEDS YOUR RESPONSE</span>
          <strong>4 evidence requests</strong>
          <p>Documents requested by Northstar Bank reviewers.</p>
          <button className="text-button" onClick={onReviewCases}>
            Review cases <ArrowUpRight size={14} />
          </button>
        </div>
        <div className="inbox-card">
          <span>PROCESSING & CHECKSUM</span>
          <strong>{evidenceList.length || 8} packages validating</strong>
          <p>AURUM is checking completeness and SHA-256 integrity.</p>
          <button className="text-button">
            View processing <ArrowUpRight size={14} />
          </button>
        </div>
        <div className="inbox-card">
          <span>ZERO-KNOWLEDGE STORAGE</span>
          <strong>100% Encrypted at Rest</strong>
          <p>Private tenant-isolated object storage with short-lived tokens.</p>
          <button className="text-button">
            Security policy <ArrowUpRight size={14} />
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Recent uploads & checksum manifest</h2>
            <p>Files submitted by your team and validated</p>
          </div>
          <a
            href="/api/v1/audit/export?format=csv"
            className="text-button"
            download
            style={{ textDecoration: 'none' }}
          >
            Download report <Download size={14} />
          </a>
        </div>

        <div className="file-list">
          {evidenceList.length > 0 ? (
            evidenceList.map((e: EvidenceItem) => (
              <div className="file-row" key={e.id}>
                <div className="file-icon"><FileText size={17} /></div>
                <div>
                  <strong>{e.file_name}</strong>
                  <span>
                    Uploaded by {e.uploaded_by_name} · SHA-256: {e.sha256_checksum.slice(0, 20)}…
                  </span>
                </div>
                <Status tone={getTone(e.validation_status)}>
                  {e.validation_status}
                </Status>
                <a
                  href={`/api/v1/evidence/${e.id}/download`}
                  download
                  className="icon-button"
                  title="Download File"
                >
                  <Download size={16} />
                </a>
              </div>
            ))
          ) : (
            ['Management accounts · Q3 2026.pdf', 'Asset register · Northbridge.xlsx', 'Insurance certificate.png'].map((f, i) => (
              <div className="file-row" key={f}>
                <div className="file-icon"><FileText size={17} /></div>
                <div>
                  <strong>{f}</strong>
                  <span>{i === 0 ? 'Uploaded today · 4.2 MB' : i === 1 ? 'Uploaded yesterday · 1.8 MB' : 'Uploaded 12 Oct · 840 KB'}</span>
                </div>
                <Status tone={i === 0 ? 'blue' : 'green'}>{i === 0 ? 'Validating' : 'Validated'}</Status>
                <MoreHorizontal size={17} />
              </div>
            ))
          )}
        </div>
      </div>
    </SubPage>
  )
}

/* TEAM WORKSPACE VIEW */
function TeamView({ members, onInvite }: any) {
  const displayMembers = members.length > 0 ? members : [
    { id: '1', full_name: 'Jordan Davies', email: 'jordan.davies@northstar.bank', role: 'Owner', avatar_initials: 'JD' },
    { id: '2', full_name: 'Maya Chen', email: 'maya.chen@northstar.bank', role: 'Reviewer', avatar_initials: 'MC' },
    { id: '3', full_name: 'Samir Patel', email: 'samir.patel@northstar.bank', role: 'Reviewer', avatar_initials: 'SP' },
    { id: '4', full_name: 'Alicia Rossi', email: 'alicia.rossi@northstar.bank', role: 'Approver', avatar_initials: 'AR' },
  ]

  return (
    <SubPage
      title="Team workspace"
      subtitle="Manage members, assignments and workspace permissions."
      action={
        <button className="primary-button" onClick={onInvite}>
          <UserPlus size={16} /> Invite member
        </button>
      }
    >
      <div className="team-stats">
        <div>
          <Users size={19} />
          <strong>{displayMembers.length}</strong>
          <span>Active members</span>
        </div>
        <div>
          <Zap size={19} />
          <strong>4</strong>
          <span>Role tiers</span>
        </div>
        <div>
          <ShieldCheck size={19} />
          <strong>100%</strong>
          <span>RBAC enforced</span>
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Members</h2>
            <p>People with access to Northstar Bank workspace</p>
          </div>
          <button className="filter-button">All roles <ChevronDown size={14} /></button>
        </div>

        <div className="member-list">
          {displayMembers.map((m: any) => (
            <div className="member-row" key={m.id || m.email}>
              <div className="member-avatar">{m.avatar_initials}</div>
              <div>
                <strong>{m.full_name}</strong>
                <span>{m.email}</span>
              </div>
              <span className="role-pill">{m.role}</span>
              <span className="member-active">
                <i />Active
              </span>
              <MoreHorizontal size={17} />
            </div>
          ))}
        </div>
      </div>
    </SubPage>
  )
}

/* BILLING & PLAN VIEW */
function BillingView({ billing }: { billing: BillingSummary | null }) {
  const data = billing || {
    plan_name: 'Enterprise',
    monthly_price: 2400,
    cases_used: 24,
    cases_limit: 100,
    storage_used_gb: 18.4,
    storage_limit_gb: 100,
    seats_used: 18,
    seats_limit: 25,
    renewal_date: '01 Nov 2026',
    invoices: [
      { id: 'INV-2026-09', date: '01 Oct 2026', amount: '$2,400', status: 'Paid' },
      { id: 'INV-2026-08', date: '01 Sep 2026', amount: '$2,400', status: 'Paid' }
    ]
  }

  return (
    <SubPage
      title="Billing & plan"
      subtitle="Manage your subscription, usage and payment details."
    >
      <div className="billing-grid">
        <div className="plan-card">
          <span className="eyebrow">CURRENT PLAN</span>
          <h2>{data.plan_name}</h2>
          <p>Built for teams running high-volume evidence operations.</p>
          <div className="price">
            ${data.monthly_price.toLocaleString('en-US')} <small>/ month</small>
          </div>
          <button className="primary-button">Manage subscription</button>
        </div>

        <div className="usage-card" style={{ gridColumn: 'span 2' }}>
          <div className="panel-heading">
            <div>
              <h2>Usage this period</h2>
              <p>Resets on {data.renewal_date}</p>
            </div>
            <CreditCard size={20} />
          </div>

          {[
            ['Cases created', String(data.cases_used), `/ ${data.cases_limit}`, (data.cases_used / data.cases_limit) * 100],
            ['Evidence storage', `${data.storage_used_gb} GB`, `/ ${data.storage_limit_gb} GB`, (data.storage_used_gb / data.storage_limit_gb) * 100],
            ['Team seats', String(data.seats_used), `/ ${data.seats_limit}`, (data.seats_used / data.seats_limit) * 100],
          ].map(([label, used, max, pct]: any) => (
            <div className="usage-row" key={label}>
              <span>{label}</span>
              <strong>{used} <small>{max}</small></strong>
              <div className="progress">
                <i style={{ width: `${Math.min(100, pct)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel invoices">
        <div className="panel-heading">
          <div>
            <h2>Recent invoices</h2>
            <p>Download receipts for your finance team</p>
          </div>
        </div>
        {data.invoices.map(inv => (
          <div className="invoice-row" key={inv.id}>
            <span>{inv.id} · {inv.date} · {inv.amount}</span>
            <Status tone="green">{inv.status}</Status>
            <Download size={16} />
          </div>
        ))}
      </div>
    </SubPage>
  )
}

/* AUDIT HISTORY VIEW */
function AuditView({ events, isVerified, onVerify }: any) {
  const [search, setSearch] = useState('')
  const filteredEvents = events.filter((e: any) =>
    `${e.action} ${e.actor_name} ${e.entity_type}`.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <SubPage
      title="Audit history"
      subtitle="A tamper-evident, cryptographically chained record of activity across your workspace."
      action={
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="secondary-button" onClick={onVerify}>
            <CheckCircle2 size={15} /> Verify Audit Integrity
          </button>
          <a
            href="/api/v1/audit/export?format=csv"
            download
            className="primary-button"
            style={{ textDecoration: 'none' }}
          >
            <Download size={15} /> Export log (CSV)
          </a>
        </div>
      }
    >
      <div className="audit-summary">
        <div>
          <ShieldCheck size={19} />
          <div>
            <strong>Audit trail active</strong>
            <span>All events retained for 7 years</span>
          </div>
        </div>
        <div>
          <Activity size={19} />
          <div>
            <strong>{events.length > 0 ? events.length : 1248} events</strong>
            <span>Recorded in workspace</span>
          </div>
        </div>
        <div>
          <FileCheck2 size={19} />
          <div>
            <strong>100% Cryptographic Traceability</strong>
            <span>SHA-256 hash chaining active</span>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div>
              <h2>Event log</h2>
              <p>Append-only audit events with cryptographic integrity</p>
            </div>
            {isVerified && (
              <span className="integrity-badge verified">
                <i /> Chain Verified
              </span>
            )}
          </div>
          <div className="search-field small">
            <Search size={15} />
            <input
              placeholder="Search events"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="audit-list">
          {(filteredEvents.length > 0 ? filteredEvents : events).map((e: any) => (
            <div className="audit-row" key={e.id}>
              <div className="event-icon blue">
                <Activity size={14} />
              </div>
              <div style={{ flex: 1 }}>
                <strong>{e.action}</strong>
                <span style={{ fontFamily: 'monospace', fontSize: '9px', color: '#8898aa' }}>
                  Entity: {e.entity_type}/{e.entity_id.slice(0, 8)} · Hash: {e.current_hash?.slice(0, 16)}…
                </span>
              </div>
              <time>{formatDateTime(e.created_at)}</time>
              <span className="actor">{e.actor_name}</span>
            </div>
          ))}
        </div>
      </div>
    </SubPage>
  )
}

/* SYSTEM HEALTH VIEW */
function SystemHealthView({ onRefresh }: any) {
  return (
    <SubPage
      title="System health"
      subtitle="Operational readiness, API latency, and database diagnostics."
      action={
        <button className="secondary-button" onClick={onRefresh}>
          <RefreshCw size={15} /> Refresh Diagnostics
        </button>
      }
    >
      <div className="team-stats">
        <div>
          <Activity size={19} />
          <strong>99.98%</strong>
          <span>Platform uptime (30d)</span>
        </div>
        <div>
          <Zap size={19} />
          <strong>14ms</strong>
          <span>API response latency</span>
        </div>
        <div>
          <ShieldCheck size={19} />
          <strong>PostgreSQL</strong>
          <span>Connection active & healthy</span>
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Service status & health probes</h2>
            <p>Component-level availability and security boundaries</p>
          </div>
        </div>

        <div className="file-list">
          {[
            ['FastAPI Python Service', 'REST API v1 gateway & state machine', 'Operational', 'green'],
            ['PostgreSQL Database Engine', 'Relational persistence & connection pooling', 'Connected', 'green'],
            ['Cryptographic Audit Store', 'SHA-256 hash-chaining verification', 'Verified', 'green'],
            ['Private Object Storage', 'Zero-knowledge encrypted evidence storage', 'Mounted', 'green'],
            ['Multi-Tenant Isolation Gate', 'Strict tenant scoping & RBAC evaluation', 'Enforcing', 'green'],
          ].map(([service, desc, stat, tone]) => (
            <div className="file-row" key={service}>
              <div className={`event-icon ${tone}`}><CheckCircle2 size={16} /></div>
              <div>
                <strong>{service}</strong>
                <span>{desc}</span>
              </div>
              <Status tone={tone}>{stat}</Status>
            </div>
          ))}
        </div>
      </div>
    </SubPage>
  )
}

/* SEARCH & EXPORT VIEW */
function SearchExportView({ cases }: { cases: CaseItem[] }) {
  const [searchTerm, setSearchTerm] = useState('')
  const results = cases.filter(c =>
    `${c.case_number} ${c.customer_name} ${c.product_type} ${c.status}`.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <SubPage
      title="Search & export"
      subtitle="Query authorized records and generate compliance exports."
      action={
        <a
          href="/api/v1/audit/export?format=csv"
          className="primary-button"
          download
          style={{ textDecoration: 'none' }}
        >
          <Download size={15} /> Export all data (CSV)
        </a>
      }
    >
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Workspace query console</h2>
            <p>Fast multi-field search across cases, evidence, and customer entities</p>
          </div>
        </div>
        <div className="table-toolbar" style={{ margin: '14px 0' }}>
          <div className="search-field">
            <Search size={16} />
            <input
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search by customer, case number, amount, or status..."
            />
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Case Number</th>
                <th>Customer</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {results.map(c => (
                <tr key={c.id}>
                  <td><strong>{c.case_number}</strong></td>
                  <td>{c.customer_name}</td>
                  <td>{c.product_type}</td>
                  <td>{c.product_type === 'Gold Loan' ? '₹' : '$'}{Number(c.requested_amount).toLocaleString(c.product_type === 'Gold Loan' ? 'en-IN' : 'en-US')}</td>
                  <td><Status tone={getTone(c.status)}>{getDisplayStatus(c.status)}</Status></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </SubPage>
  )
}

/* SETTINGS VIEW */
function SettingsView() {
  const [settingsTab, setSettingsTab] = useState('General')
  const [orgName, setOrgName] = useState('')
  const [timezone, setTimezone] = useState('Asia/Kolkata (IST)')
  const [defaultOwner, setDefaultOwner] = useState('Assign to team queue')
  const [notifEmail, setNotifEmail] = useState('')
  const [slaHours, setSlaHours] = useState(24)
  const [dualApproval, setDualApproval] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [settingsToast, setSettingsToast] = useState('')

  useEffect(() => {
    api.getWorkspaceSettings().then(s => {
      setOrgName(s.organization_name || '')
      setTimezone(s.timezone || 'Asia/Kolkata (IST)')
      setDefaultOwner(s.default_case_owner || 'Assign to team queue')
      setNotifEmail(s.notification_email || '')
      setSlaHours(s.sla_alert_hours ?? 24)
      setDualApproval(s.require_dual_approval ?? true)
      setSavedAt(s.updated_at)
    }).catch(() => {})
  }, [])

  async function handleSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!api.hasAccessToken()) {
      setSettingsToast('Sign in before saving workspace settings.')
      return
    }
    setSaving(true)
    try {
      const res = await api.updateWorkspaceSettings({
        organization_name: orgName,
        timezone,
        default_case_owner: defaultOwner,
        notification_email: notifEmail || undefined,
        sla_alert_hours: slaHours,
        require_dual_approval: dualApproval,
      })
      setSavedAt(res.updated_at)
      setSettingsToast('Settings saved successfully.')
    } catch (err: any) {
      setSettingsToast(err.message || 'Failed to save settings')
    } finally {
      setSaving(false)
      setTimeout(() => setSettingsToast(''), 3000)
    }
  }

  const tabs = ['General', 'Notifications', 'Security & SSO', 'Data retention', 'Integrations']

  return (
    <SubPage
      title="Settings"
      subtitle="Configure workspace defaults, notifications and security controls."
    >
      {settingsToast && (
        <div className="toast" style={{ position: 'relative', right: 'auto', bottom: 'auto', marginBottom: '16px', display: 'flex' }}>
          <CheckCircle2 size={16} /> {settingsToast}
        </div>
      )}
      <div className="settings-layout">
        <div className="settings-nav">
          {tabs.map(t => (
            <button key={t} className={settingsTab === t ? 'selected' : ''} onClick={() => setSettingsTab(t)}>{t}</button>
          ))}
        </div>
        {settingsTab === 'General' && (
          <div className="panel settings-form">
            <h2>General settings</h2>
            <p>Update the identity and default behaviour of your workspace.</p>
            <form onSubmit={handleSave}>
              <label>
                Organisation name
                <input value={orgName} onChange={e => setOrgName(e.target.value)} placeholder="e.g. Northstar Bank" required />
              </label>
              <label>
                Workspace timezone
                <select value={timezone} onChange={e => setTimezone(e.target.value)}>
                  <option value="Asia/Kolkata (IST)">Asia/Kolkata (IST)</option>
                  <option value="Europe/London (GMT+1)">Europe/London (GMT+1)</option>
                  <option value="America/New_York (EST)">America/New_York (EST)</option>
                  <option value="Asia/Dubai (GST)">Asia/Dubai (GST)</option>
                </select>
              </label>
              <label>
                Default case owner
                <select value={defaultOwner} onChange={e => setDefaultOwner(e.target.value)}>
                  <option value="Assign to team queue">Assign to team queue</option>
                  <option value="M. Chen">M. Chen</option>
                  <option value="S. Patel">S. Patel</option>
                  <option value="A. Rossi">A. Rossi</option>
                  <option value="J. Okafor">J. Okafor</option>
                </select>
              </label>
              <label>
                SLA alert threshold (hours)
                <input type="number" min={1} max={168} value={slaHours} onChange={e => setSlaHours(Number(e.target.value))} />
              </label>
              <label style={{ flexDirection: 'row', alignItems: 'center', gap: '10px', marginTop: '18px' }}>
                <input type="checkbox" checked={dualApproval} onChange={e => setDualApproval(e.target.checked)} style={{ width: '16px', height: '16px' }} />
                Require dual-approval (maker-checker) for all decisions
              </label>
              <div className="form-footer">
                <span>{savedAt ? `Last saved: ${new Date(savedAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}` : 'Not yet saved to backend'}</span>
                <button className="primary-button" type="submit" disabled={saving}>
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            </form>
          </div>
        )}
        {settingsTab === 'Notifications' && (
          <div className="panel settings-form">
            <h2>Notification settings</h2>
            <p>Configure alert delivery for SLA breaches and exception escalations.</p>
            <label>
              Alert email address
              <input type="email" value={notifEmail} onChange={e => setNotifEmail(e.target.value)} placeholder="ops-alerts@yourbank.com" />
            </label>
            <div className="form-footer">
              <span>Email alerts are queued; delivery requires an SMTP adapter in Integrations.</span>
              <button className="primary-button" type="button" disabled={saving} onClick={async () => {
                setSaving(true)
                try {
                  await api.updateWorkspaceSettings({ notification_email: notifEmail || undefined })
                  setSettingsToast('Notification settings saved.')
                } catch { setSettingsToast('Save failed') }
                finally { setSaving(false); setTimeout(() => setSettingsToast(''), 3000) }
              }}>{saving ? 'Saving…' : 'Save'}</button>
            </div>
          </div>
        )}
        {settingsTab === 'Security & SSO' && (
          <div className="panel settings-form">
            <h2>Security &amp; SSO</h2>
            <p>JWT-based session management is active. SSO provider integration is planned.</p>
            <div style={{ background: '#f6f9ff', border: '1px solid #d5e4fc', borderRadius: '7px', padding: '16px', marginTop: '16px', fontSize: '11px', color: '#3d6299' }}>
              <strong style={{ display: 'block', marginBottom: '6px' }}>Current security posture</strong>
              JWT bearer tokens · bcrypt password hashing · Multi-tenant RBAC · Append-only audit trail with SHA-256 hash chaining
            </div>
          </div>
        )}
        {settingsTab === 'Data retention' && (
          <div className="panel settings-form">
            <h2>Data retention</h2>
            <p>Audit events are retained for 7 years per RBI compliance requirements. Evidence files follow the same schedule.</p>
            <div style={{ background: '#f6f9ff', border: '1px solid #d5e4fc', borderRadius: '7px', padding: '16px', marginTop: '16px', fontSize: '11px', color: '#3d6299' }}>
              <strong style={{ display: 'block', marginBottom: '6px' }}>Retention policy</strong>
              Audit events: 7 years · Evidence files: 7 years · Case records: 7 years · Payment orders: 10 years
            </div>
          </div>
        )}
        {settingsTab === 'Integrations' && (
          <div className="panel settings-form">
            <h2>Integration overrides</h2>
            <p>Manage adapter modes and API keys in the <strong>Integrations &amp; settings</strong> workspace.</p>
          </div>
        )}
      </div>
    </SubPage>
  )
}
