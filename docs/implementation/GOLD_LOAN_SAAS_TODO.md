# AURA Gold Loan SaaS Prototype TODO

**Updated:** 16 October 2026  
**Scope:** Extend the existing Next.js + FastAPI application without replacing its UI or duplicating its backend. This is a development prototype plan, not a production certification.

## Status key

- `[x]` Existing usable capability retained and exposed in the workspace.
- `[~]` Partial implementation or simulator; safe for clearly labelled development flows only.
- `[ ]` Not implemented or not verified end to end.

## Work completed in this pass

- [x] Preserve the current sidebar, typography, navigation and screens.
- [x] Add an overview module map covering all 22 requested business capabilities.
- [x] Add live counts for working, simulated, and partial/planned modules (counts derive from the module status list).
- [x] Make module cards navigate to their related existing screen and explain partial/simulated status.
- [x] Add responsive styling and a visible prototype boundary for simulator/provider events.
- [x] Reconcile outstanding work against the existing requirement and repository audits instead of adding a competing Java backend.
- [x] Persist tenant-scoped gold-loan workflow records linked to a Gold Loan case, including consent, collateral snapshots, valuation snapshots, and a per-application event timeline.
- [x] Create tenant-scoped customer profiles and reuse them by optional bank customer reference without fuzzy name-based merging.
- [x] Record KYC simulator outcomes as indeterminate; retain only masked identifiers and simulator statuses, never raw PAN/Aadhaar inputs.
- [x] Record signed-assay simulator events as simulated and explicitly mark the device as unauthenticated.
- [x] Enforce maker-checker on approvals and block gold-loan approval until accepted consent, provider-verified KYC and trusted appraisal exist.
- [x] Add workspace-filtered application list/detail APIs and connect the Gold Loan station to persisted intake, consent, KYC, assay and valuation actions.

## Current prototype coverage

| Capability | State | Existing entry point | Next work |
|---|---|---|---|
| Identity and access | `[~]` | Sign-in, team workspace, protected API | Complete role/permission matrix and branch scope on every operation. |
| Bank, tenant and branches | `[~]` | Organization workspace | Add branch entities, assignments, tenant administration and isolation coverage. |
| Customer profile/history | `[~]` | Gold Loan LOS intake | Profiles link to applications and can be reused by bank reference; authorized merge/deduplication tools remain. |
| Loan applications | `[~]` | Gold Loan LOS and My cases | Core record and timeline persist; add customer master, branch scopes and full transitions. |
| Consent | `[~]` | KYC simulator | Version and purpose persist; add customer evidence, revocation history and approved wording. |
| KYC and verification | `[~]` | KYC simulator | Consent gate and indeterminate masked attempts persist; connect contracted providers and reconciliation. |
| Documents and evidence | `[x]` | Evidence inbox | Link immutable evidence versions to customer/application/ornament and retention policy. |
| Gold inventory | `[~]` | Assay station | Valuation snapshots persist item measurements; add packet identity, evidence and inventory lifecycle. |
| Analyzer and calibration | `[~]` | Assay simulator | Enroll real device keys, validate calibration, three-spot readings and replay rules. |
| Valuation and eligibility | `[~]` | Eligibility calculator | Persisted trace/rate/policy version is marked simulated; add approved feeds and policy publication. |
| Underwriting and approval | `[~]` | Case review | Maker-checker and gold approval gates now block unsafe approval; implement verified decision path and delegated limits. |
| Exceptions | `[~]` | Case workflow | Persist ownership, SLA, resolution evidence and controlled override paths. |
| Custody and vault | `[~]` | Vault & Servicing | Persist dual-custodian events, seal identifiers, location and release controls. |
| LOS/LMS booking | `[ ]` | Integrations settings | Implement bank adapter contracts, idempotency, status inquiry and reconciliation. |
| Disbursement | `[~]` | Vault & Servicing | Remove simulator settlement claims; connect approved payout provider and durable ledger. |
| Repayments and closure | `[~]` | Payments | Complete webhook/reconciliation, value-dated ledger, reversals, closure and collateral release. |
| Collections and auctions | `[~]` | Vault & Servicing | Configure policies, scheduler, notices, NPA, auction settlement and surplus/refund. |
| Audit and compliance | `[x]` | Audit history | Extend event coverage to each gold-loan mutation and verify retention/export controls. |
| Notifications and SLA | `[~]` | Overview/system health | Add persisted tasks, due-time calculation, delivery attempts and escalation. |
| Analytics | `[x]` | Overview | Replace sample/fallback dashboard values with role-scoped production aggregations. |
| SaaS subscriptions | `[~]` | Billing & plan | Implement branch entitlements, invoices, renewal state and contract-based usage. |
| Platform administration | `[~]` | Settings/integrations | Add approval and effective-date workflow for policy/reference-data changes. |
| Security and operations | `[~]` | System health/integrations | Add alerting, job recovery, secrets rotation, backup/restore evidence and incident flow. |

## Ordered implementation backlog

### P0 — Complete the prototype vertical slice

- [~] Persist tenant-scoped customer profiles, gold-loan application, consent, collateral, valuation and workflow-event records; exception records and branch-scoped records remain.
- [x] Connect UI actions to persisted application records and show per-application events with actor, time, stage and simulated marker.
- [~] Enforce consent before KYC and prevent approval while KYC/appraisal are not provider/device verified; production-stage progression, evidence gates and booking/servicing remain.
- [ ] Make all simulator inputs/results explicitly `is_simulated`, prohibit them from creating real approval, booking, disbursement or settlement states, and avoid presenting sample rate data as an authoritative feed.
- [ ] Persist append-only audit events for every gold-loan workflow action and preserve calculation/policy/rate versions for reconstruction.
- [~] Enforce bearer identity, tenant scope and maker-checker on approvals; complete role matrix and branch scope for every operation.
- [ ] Replace hardcoded overview fallbacks with empty/loading/offline states so sample cases are never mistaken for a live tenant's records.

### P1 — Integrations and lifecycle

- [ ] Define provider interfaces and sandbox contracts for identity, bureau, gold rate, analyzer gateway, document signing, LOS/LMS, payout, notifications and auctions.
- [ ] Add idempotency keys, request/response references, status inquiries and a reconciliation queue for ambiguous external outcomes.
- [ ] Implement custody handoffs and release as separately authorized, auditable transitions.
- [ ] Complete repayment webhook signature checks, event idempotency, posting/reversal and closure calculation before collateral release.
- [ ] Add persisted SLA tasks and delivery-attempt history for notifications.

### P2 — SaaS and operational maturity

- [ ] Add bank/branch administration, member assignment and contract-governed subscriptions.
- [ ] Add policy/rate publication with effective dates, approval, rollback and historical references.
- [ ] Add operational incidents, integration health history, background-job recovery and backup/restore runbooks.
- [ ] Add tenant-isolation, role matrix, transition, idempotency and failure-recovery acceptance coverage.
- [ ] Validate retention, privacy, residency, regulatory and financial rules with each bank before production use.

## Completion boundary

The core prototype workflow now persists customer profiles, application intake, versioned consent records, masked KYC simulator attempts, simulated assay events, collateral/valuation snapshots, an application timeline and append-only tenant audit events. Approval is blocked until provider-verified KYC and trusted appraisal exist, and creator self-approval is rejected. Provider integrations, physical device verification, bank settlement, approved lending policy, production-grade data retention and disaster recovery require lender-specific credentials, contracts, policy decisions or infrastructure; they cannot be represented as completed by a local prototype. Keep the app labelled as a development prototype until those items are implemented and independently verified.
