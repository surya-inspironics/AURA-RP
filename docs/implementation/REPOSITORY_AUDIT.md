# AURA Repository Audit

**Audit date:** 21 October 2026  
**Audit type:** Read-only application audit; no source/configuration implementation changes were made. Seven audit documents are the only intended deliverables.  
**Verification boundary:** Static repository inspection and baseline commands listed in `TEST_COVERAGE_AND_BASELINE.md`; not a penetration test, provider certification, regulatory review, or production-readiness assessment.

## 1. Executive assessment

**Current classification: development-stage application with useful working case/evidence capabilities, persisted gold-loan intake snapshots, local deterministic calculations, and several explicit simulators. It is not a commercial, production-ready lending platform.**

The code contains more working backend behavior than older copies of `REPOSITORY_AUDIT.md` described. It also contains significant security and business-completion gaps. In particular, general API routes retain a demo-identity fallback and do not always prove tenant membership; gold-loan payout, custody, KYC, assay, documents and auction are simulated or unavailable; a trusted gold rate and physical assay are not established; the loan ledger/booking lifecycle is absent; migration/recovery evidence is missing; the baseline is red.

**Do not use current outputs as confirmed KYC, physical assay, approved lending eligibility, bank disbursal, loan balance, custody, payment settlement, auction, or regulatory classification.**

## 2. Repository root, Git state, and scope

- The executable Git repository root is `C:\AURA\aura-product-implementation`, branch `develop`, tracking `origin/develop`.
- The parent `C:\AURA` directory is not a Git repository. It contains a separate `backend`, `frontend`, `contracts`, and `infra` tree, but those directories have no source files in this checkout; domain-named directories there are empty.
- The nested repository worktree was already dirty before this audit. Its pre-audit status included modified tracked files `app/globals.css`, `app/page.tsx`, `backend/app/gold_loan/integrations/gold_rate_adapter.py`, `backend/app/main.py`, `backend/app/models/entities.py`, `backend/app/routers/decisions.py`, `backend/app/routers/gold_loan.py`, `backend/app/routers/system.py`, `backend/app/services/decision_service.py`, `components/GoldLoanStationView.tsx`, `components/PaymentsView.tsx`, `lib/api.ts`, `next.config.mjs`; untracked `Dockerfile.backend`, `components/GoldLoanCalculator.tsx`, `components/GoldRateTicker.tsx`, `docker-compose.yml`, `docs/implementation/GOLD_LOAN_SAAS_TODO.md`, `start.bat`, `start.sh`, and `.venv/`.
- These pre-existing changes were not reviewed as authored changes, reverted, or otherwise altered. Build regenerated `next-env.d.ts`; that specific generated diff was restored to its pre-audit state.
- The parent workspace has an `aura-product-implementation.zip`; its name inventory did not contain the referenced gold-loan master prompt or source requirement/specification files.
- Audit reports are under `docs/implementation/`. Existing `REQUIREMENT_TRACEABILITY_MATRIX_I0_I7.md`, `AURA_GOLD_LOAN_RECONCILIATION_AUDIT.md`, `GOLD_LOAN_SAAS_TODO.md`, and `docs/adr/ADR-001-STACK-RECONCILIATION-MODULAR-FASTAPI.md` remain historical inputs. Some conflict with current code or with each other.

## 3. Technology and architecture found

### Frontend

- Next.js 16 App Router, React 19, TypeScript, Tailwind CSS, `lucide-react`.
- Routes found: `/`, `/sign-in`, `/sign-up`, `/api/auth/[...all]`; other major product workspaces are views within the main app page rather than separate route segments.
- Main UI: `app/page.tsx`; styling: `app/globals.css`; gold-loan, payment, integration and servicing panels under `components/`.
- API facade: `lib/api.ts`; most browser requests go through `/api/v1` and Next rewrites to FastAPI.
- The overview contains fallback demo cases and catches failures by substituting defaults/empty lists. Thus a rendered UI or successful toast is not proof of server persistence.

### Backend

- Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, bcrypt, PyJWT.
- Entrypoint `backend/run.py`; app setup `backend/app/main.py`; API prefix `/api/v1`.
- Routers: auth, cases, evidence, validation, decisions, audit, analytics, team, billing, system, integrations, gold-loan.
- Business services: case, evidence, validation, decision, audit, analytics and billing.
- Gold-loan services: eligibility, custody, servicing, and collections calculators.
- Integration adapter set: payment, payout, identity, credit bureau, screening, gold rate, device, document signing, notifications and auction.
- Pattern: frontend API facade → router → service/engine → SQLAlchemy database or local filesystem. This is a layered FastAPI application; it is not currently implemented as populated per-domain modules under the separate top-level `C:\AURA\backend\app\modules` tree.

### Database, persistence and schemas

- SQLAlchemy entities include tenant, user, membership, case, payment order, gold-loan customer/application/consent/collateral/valuation/workflow event, evidence, rule version, validation finding, decision, exception, audit event, subscription, invoice and tenant settings.
- SQLAlchemy request session uses configured `DATABASE_URL` or SQLite fallback. Docker Compose describes PostgreSQL.
- Pydantic schemas validate much of the HTTP boundary; TypeScript API interfaces describe the browser boundary.
- Gold-loan application, consent, KYC simulator marker, collateral snapshot, valuation snapshot, timeline event, audit events, and repayment orders are persisted. Many other gold-loan “servicing” results are stateless calculations or process-local data.
- No migration files were found under nested `backend/migrations`; startup calls `Base.metadata.create_all()` and runs seed-if-absent. Database schema evolution and production bootstrap are not governed by a demonstrated migration process.
- Evidence payloads are local files under tenant/case paths, not a verified private object-store integration.

## 4. Feature status summary

| Area | Status | Verified implementation boundary |
|---|---|---|
| Sign-in / registration | `PARTIAL` | FastAPI password/JWT registration/login and bcrypt exist. UI stores JWT in localStorage. A separate Better Auth + Drizzle path is also present. |
| Tenant isolation | `PARTIAL / HIGH RISK` | Many queries filter by tenant; strict gold-loan helper checks membership. General helper falls back to a demo user and accepts a tenant header without confirming membership. No branch model. |
| Cases | `PARTIAL` | CRUD/list/detail and allowed status transition table exist, with tenant filters and audit events. Auth/role and workflow gates are incomplete. |
| Evidence | `PARTIAL` | Upload, extension/size check, checksum metadata, local storage, list and tenant-scoped download. Memory, MIME/content, checksum-on-read, malware, immutable version and production storage controls are absent. |
| Validation | `PARTIAL` | Four deterministic rules persist findings. Version parameter does not select a version; evidence integrity and sanctions checks are not real. |
| Decisions | `PARTIAL` | Decision persistence, actor field, rationale, role check for approval and creator self-approval guard. Generic state gates are missing; gold-loan approvals are intentionally blocked while required evidence is simulated. |
| Audit | `PARTIAL` | SHA-256 chain and export endpoints. Verification only checks previous-hash linkage; no digest recomputation, enforced append-only storage, or complete mutation coverage. |
| Gold-loan origination | `PARTIAL` | Tenant-scoped customer/application and workflow records link to a Gold Loan case. Customer identity, branches and full state machine are incomplete. |
| Assay | `MOCKED` | Simulated readings can be HMAC-signed by app-generated process secret. Hardcoded test devices; no physical-device trust. Persisted user input is marked simulated. |
| Valuation / eligibility | `PARTIAL` | Integer arithmetic and calculation trace exist; input rate/limits may be sample/user-controlled; saved preview marked simulated. |
| KYC, screening, bureau | `MOCKED` | Synthetic adapter responses, explicitly non-provider-verified. Gold workflow preserves KYC as indeterminate. |
| Maker-checker | `PARTIAL` | Self-approval prevention in generic flow; disbursal simulator checks distinct supplied strings. No identity-bound payout authority; gold approval is currently blocked. |
| Custody | `MOCKED` | In-memory simulator labels no physical sealing or release. |
| Loan booking / payout | `MOCKED / MISSING` | Bank payout simulator returns no-provider-confirmed state. No real bank connection, durable payout record or loan account/ledger. |
| Repayments | `PARTIAL` | Test-mode Razorpay API order creation and payment lookup/signature verification; order is persisted. No live funds or loan ledger update. |
| Servicing / MTM / collections | `PARTIAL` | Stateless arithmetic endpoints; loan IDs/balances/weights are caller input. No scheduled durable account processing. |
| Auction | `MOCKED` | Synthetic bid/refund math; no auction or settlement. |
| Analytics / billing | `MOCKED / PARTIAL` | Some queries are real; trend series, reviewer data, averages, usage fallbacks, invoices, plan and renewal include fixed/demo values. |
| Team | `PARTIAL` | Membership listing/invite. Fixed welcome password; no verified invitation acceptance flow or full role governance. |
| Integrations | `MOCKED / PARTIAL` | Ten adapter-shaped classes; only Razorpay test environment is contacted in the repayment path. Remaining providers are absent or simulator-only. |
| Jobs / monitoring / deployment | `MISSING / PARTIAL` | Health route, middleware headers, Dockerfile/Compose and prose deployment guide exist. No background work, CI workflows, metrics, alerts, backup/restore proof. |

Refer to `REQUIREMENT_TRACEABILITY_MATRIX.md` for the C-01–C-10 and I-0–I-7 mapping; `INTEGRATION_STATUS_MATRIX.md` for all adapters; `IMPLEMENTATION_GAP_REGISTER.md` for acceptance criteria per gap; `SECURITY_AND_ARCHITECTURE_RISKS.md` for security findings.

## 5. Main end-to-end flows inspected

### Case/evidence/review

`app/page.tsx` calls methods in `lib/api.ts` → Next rewrite in `next.config.mjs` → FastAPI router → service → SQLAlchemy.

- Case creation calls `/cases/`; `CaseService.create_case` saves a case, sets initial status/SLA, and records audit.
- Evidence upload calls `/evidence/upload`; router resolves case tenant, reads full file, then `EvidenceService.save_evidence` checks extension and byte length, hashes, writes local file, saves metadata and audit.
- Validation calls `/validation/run`; `ValidationService.run_validation` deletes prior findings, evaluates four hardcoded rules, updates status and writes audit.
- Decision calls `/decisions/`; router checks approval role, service applies creator self-approval check and updates case status.

The flow is functional in development but not complete production evidence processing: the default dependency is permissive, validation semantics overstate provider checks, warnings can advance, file integrity is not verified on download, and there are no branch, durable exception or full decision gates.

### Gold-loan workflow

`GoldLoanStationView.tsx` and `GoldLoanCalculator.tsx` call `lib/api.ts` methods → `routers/gold_loan.py` → database snapshots or pure engines. Intake, consent, simulated KYC/assay markers, valuation previews, timeline records and audit events persist. Valuation is marked simulated, and a gold decision cannot be approved while KYC/appraisal is unverified.

Payments UI supports test-mode Razorpay order and payment verification. Vault, servicing and collections panels invoke stateless calculations or in-memory simulators. There is no production loan account lifecycle from approval to booking, payout, postings, servicing and closure.

## 6. Hardcoded, seeded, fallback and simulated behavior

- Seed creates a named demo bank, five demo users, baseline cases/evidence, an active rule set and subscription; credentials use a fixed demo password in `database/seed.py`.
- `get_current_tenant_and_user` falls back to the first user and tenant.
- UI initial case array and API failure handling can display fallback data.
- Analytics generates artificial trend/funnel/workload/average/at-risk values.
- Billing returns demonstration invoices, fixed plan/renewal, and fallback case/storage/seat usage.
- KYC, credit bureau, sanctions, device, disbursal, custody, e-sign, notification and auction responses have explicit simulator markers or no-provider behavior.
- Gold rates request free external sources but retain static fallback rates; these are not established as approved rates.
- NPA/provision, LTV and other numerical values are source-code constants. The report does not approve those values as regulatory policy.

## 7. Requirements, documentation and architecture decisions

The repository retains C-01–C-10, R-FIN-01, R-TEN-02, R-EVID-03, R-POL-04, and I-0–I-7 terminology in prior docs. Older documents contain materially stale claims, including that no backend exists; they also disagree on Flask/Java/Spring versus FastAPI. `ADR-001` states that the existing Next.js/FastAPI foundation is retained. It is marked approved, but the controlling master prompt and source specifications cited by old audits were not found in the repository/archive inventory.

Treat unavailable source requirements, thresholds, product rules, and provider assumptions as **missing evidence/unresolved decisions**, not as implicit approval. Obtain the correct source documents and reconcile them before coding.

## 8. Baseline checks

- Backend: `pnpm --dir C:\AURA\aura-product-implementation test:backend` — **22 passed, 4 failed, 11 warnings**. One failure is an approval expectation conflicting with creator self-approval protection; one is stale adapter naming; one is a unique payment ID collision against configured SQLite state; one is missing providerless production protection for rates.
- Frontend: `pnpm --dir C:\AURA\aura-product-implementation build` — exit code 0; however, Next output says it skipped type validation and Better Auth emitted missing base URL/default-secret warnings.
- TypeScript: `pnpm --dir C:\AURA\aura-product-implementation exec tsc --noEmit` — failed on `components/GoldLoanCalculator.tsx` access to `limits_comparison_paise` under the inferred summary type.
- Lint/typecheck scripts, CI, security scanning and E2E suite were not present/run.
- The backend test fixture operates through the configured DB engine and makes writes; the test run may have written records to local SQLite. This audit did not attempt database cleanup or rollback. See `TEST_COVERAGE_AND_BASELINE.md`.

## 9. Top blockers and next step

Top blockers: universal authentication and tenant/branch authorization; trusted assay; approved market-rate/policy; durable bank payout and loan ledger; verified KYC/screening; real custody/documents; repayment reconciliation; complete audit verification; secure evidence storage; migrations/recovery and a green, isolated CI baseline.

Recommended order: source requirements and architecture reconciliation → safe reproducible test baseline → auth/tenant/branch boundaries → persistence/migrations/audit/evidence foundation → trusted gold inputs/KYC → approved valuation and underwriting → bank booking/disbursal → payments/ledger/servicing → collections/auction → commercial entitlements and operations.

**Smallest recommended first batch:** requirements reconciliation and a disposable hermetic test/typecheck baseline. Its acceptance criteria and subsequent phase dependencies are in `PRIORITIZED_IMPLEMENTATION_PLAN.md`. No implementation work is started or authorized here.

## 10. Document index

1. `REPOSITORY_AUDIT.md` — repository scope, architecture and executive status.
2. `REQUIREMENT_TRACEABILITY_MATRIX.md` — C-01–C-10, I-0–I-7 and domain status mapping.
3. `IMPLEMENTATION_GAP_REGISTER.md` — evidence, risk, dependencies and acceptance criteria for each gap.
4. `INTEGRATION_STATUS_MATRIX.md` — integration-by-integration implementation and external needs.
5. `SECURITY_AND_ARCHITECTURE_RISKS.md` — source-level risks and unresolved decisions.
6. `TEST_COVERAGE_AND_BASELINE.md` — exact commands/results, failures, coverage and side-effect caveat.
7. `PRIORITIZED_IMPLEMENTATION_PLAN.md` — gated dependency order and proposed smallest first batch.
