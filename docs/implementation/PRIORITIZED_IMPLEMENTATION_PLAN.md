# AURA Prioritized Implementation Plan

**Audit date:** 21 October 2026  
**Status:** Audit recommendation only. No implementation is authorized by this document. Work must not start until the owner reviews and approves the source requirements, plan, and business-policy decisions.

## Guardrails

1. Preserve the current Next.js UI layout, navigation, typography, palette, and visual identity.
2. Retain the existing FastAPI/SQLAlchemy backend unless the product owner explicitly revises the approved stack decision in `docs/adr/ADR-001-STACK-RECONCILIATION-MODULAR-FASTAPI.md`.
3. Do not treat test-mode payments, simulator KYC/assay, estimated rates, simulated custody, or simulated payout/auction as production capability.
4. Do not encode unapproved regulatory or bank policy from constants/comments. Obtain policy owner sign-off and keep versioned decision records.
5. Use isolated test data stores. Never run tests or seed logic against a customer/operational database.
6. Every accepted requirement must trace to its original ID, code path, test, and release evidence.

## Dependency-ordered phases

| Order | Phase / gate | Prerequisites | Scope and exit evidence |
|---:|---|---|---|
| 0 | Requirements and architecture reconciliation | Product owner supplies controlling master prompt, MRS/PRS/SyRS/HLD/LLD and confirms approved ADR. | Preserve existing IDs; resolve stale contradictory docs; approve scope, tenant/branch, roles, workflow state machines, unit conventions and policy owners. No code until signed baseline. |
| 1 | Safe engineering baseline | Phase 0; disposable test DB configuration. | Prevent tests from touching persistent DB; make tests deterministic/no external network; resolve currently failing tests; add explicit `typecheck` and CI gates; remove build typecheck bypass only as part of a green measured change. |
| 2 | Authentication, tenant and branch security | Approved role and organization model; authoritative auth choice. | Choose Better Auth or FastAPI JWT; enforce active identity and membership on every protected route; remove demo fallback from deployable mode; define branch membership and object scope; verify cross-tenant/cross-branch denial and audit admin actions. |
| 3 | Persisted operational foundation | Phase 2; approved DB and retention policy. | Add versioned migrations; controlled seed strategy; transactional DB boundaries; audit coverage and immutable/tamper verification; private storage lifecycle, upload streaming/validation/checksum; isolated integration test harness. |
| 4 | Gold-loan trust and origination slice | Phase 0 policy decisions, Phase 2/3; customer/KYC/device provider contracts as applicable. | Customer and consent evidence; provider-backed KYC or explicitly blocked state; device gateway trust, calibration, freshness and replay controls; no manual/simulator value may satisfy production gates. |
| 5 | Valuation and underwriting | Approved rate source, unit/rounding/LTV/risk policies; trusted assay data. | Deterministic calculation trace tied to rate/policy version; input validation; reviewer/approver authority and maker-checker; exception and override lifecycle; test vectors signed by domain owners. |
| 6 | Booking, custody and disbursal | Bank/core banking contract; ledger/accounting decisions; verified eligibility/decision; branch operations process. | Durable loan account and payout state, identity-bound maker-checker, persistent idempotency, status inquiry and reconciliation, custody packet lifecycle and external confirmation. Never mark booked/settled before provider confirmation. |
| 7 | Repayments and servicing | Phase 6 ledger; payment provider sandbox contract; day-count/waterfall/value-date rules. | Test-mode provider callback/webhook and idempotency; durable journal posting/reversals; ambiguity reconciliation; interest accrual and account balance reconstruction. |
| 8 | Collections, notices, auction and closure | Approved DPD/NPA/margin-call/notice/auction policies; messaging and auction provider contracts. | Scheduled and replayable jobs; persisted notices and delivery outcomes; LTV/DPD history; authorized auction and settlement; surplus/refund, full closure and collateral release evidence. |
| 9 | SaaS entitlements and operations | Commercial plans/contracts, storage/retention, operations ownership. | Replace hardcoded billing/KPIs; enforce quotas; monitoring/logging/redaction; backup/restore drill; alert/runbook, deployment and rollback evidence. |
| 10 | Production readiness | All required providers and credentials in managed secrets; security, legal/compliance and bank sign-off. | Contract and end-to-end tests; threat-model closure; performance/resilience tests; support/incident process; recovery objectives tested; release gates and customer acceptance. |

## Top ten blockers to commercial use

1. Unauthenticated/demo-fallback and tenant-header authorization in general API routes.
2. No complete tenant/branch role-authorization model.
3. No trusted, physical assay/device trust chain; gold inputs can originate from manual simulation.
4. No approved rate feed and no fail-closed market-data path.
5. No approved/verified lending policy, calculation rounding/unit contract, or policy version publication.
6. No real bank payout, durable disbursal idempotency, settlement inquiry, or loan booking ledger.
7. No durable loan ledger, repayment webhook/reconciliation, reversal or balance recovery.
8. No physically evidenced vault custody, documented e-sign, real customer verification, or actual auction.
9. Incomplete audit tamper verification/coverage, evidence security, migrations, backup and restore.
10. Broken quality baseline: 4 backend failures, TypeScript error hidden by build configuration, no CI release gates.

## Smallest recommended first implementation batch (proposal only)

**Batch 0: Requirements and safe baseline, no UI redesign.** This is the only recommended first batch before operational feature work.

### Contents

- Obtain and identify the controlling source specification; reconcile IDs and status terminology with existing I0-I7 and C-01–C-10 documents.
- Confirm auth/session architecture and tenant/branch/role matrix.
- Establish a disposable SQLite/PostgreSQL test database so tests cannot write to `aura.db` or any configured operational DB.
- Stub external calls in tests and eliminate network-dependent baseline execution.
- Rebaseline existing backend tests, resolve failures with explicit product/test-owner decisions, and record coverage gaps.
- Add a standalone typecheck command and a CI gate after owners approve the build behavior.

### Acceptance criteria

1. Every controlling requirement has its original ID, source citation, owner, acceptance evidence, and status; conflicts are logged, not silently decided.
2. A test command is shown to use a unique disposable database; verify that the operational DB file/hash and records are unchanged before and after.
3. Unit/integration test execution makes no outbound provider requests.
4. Baseline suite is repeatable and green or has individually approved, tracked exceptions; no test is weakened merely to obtain green.
5. `tsc --noEmit` passes, and production build no longer masks type errors.
6. No frontend layout, navigation, typography, colors, or visual identity is changed.
7. No provider is described as live/verified without provider evidence.

## Decisions needed before code work

- Confirm whether this report’s nested repository path is the implementation source of truth; top-level modular directories are empty.
- Provide the authoritative gold-loan requirements document and specify whether existing `ADR-001` controls over older Java/Spring reconciliation notes.
- Confirm Indian gold-loan regulatory/business interpretations with the bank’s compliance and legal owners. This audit intentionally does not approve or restate numeric thresholds as policy.
- Select the identity, rate, KYC, bureau, AML, device, bank payout, payment, e-sign, notification, auction, storage and database providers.
- Approve deployment environment, secret management, PII retention, audit immutability, branch scope, backup/recovery objectives and incident ownership.
