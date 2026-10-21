# AURA Requirement Traceability Matrix

**Audit date:** 21 October 2026  
**Repository:** `C:\AURA\aura-product-implementation`  
**Purpose:** Trace existing repository requirement identifiers to inspected implementation and baseline evidence. This is an implementation audit, not regulatory or financial certification.

## Status vocabulary

- `IMPLEMENTED_AND_VERIFIED`: complete requirement demonstrated end to end with fitting automated evidence. No module in this audit qualifies.
- `IMPLEMENTED_UNVERIFIED`: implementation is present, but full acceptance has not been demonstrated.
- `PARTIAL`: meaningful pieces exist; one or more required controls or lifecycle segments are absent.
- `UI_ONLY`: visible interaction without a working backend/business operation for the requirement.
- `MOCKED`: output is simulated or in-memory and does not establish a real provider, device, financial, or physical event.
- `MISSING`: no relevant implementation found.
- `BLOCKED_BY_EXTERNAL_DEPENDENCY`: completion requires a named external service, contract, credential, or approval not present in the repository.

`Primary status` describes the inspected state as a whole; details distinguish live, simulated, and missing portions. Existing identifiers are retained. The original master prompt, MRS/PRS/SyRS/HLD/LLD source artifacts referenced by older notes were not found as files in the repository or inspected ZIP inventory. Therefore, `C-*`, `I-*`, `R-*`, and the terminology below are taken from existing repository documents, not independently verified against the missing source specification.

## Product and platform requirements

| Requirement ID / terminology | Primary status | Evidence in repository | Gap / acceptance evidence still required |
|---|---|---|---|
| C-01 Web client / operator console | `PARTIAL` | Next.js App Router routes `/`, `/sign-in`, `/sign-up`; dashboard and workflow screens in `app/page.tsx`; gold-loan components under `components/`. | Preserve visual identity; test each action against real APIs, authorization, loading/error/empty states, and browsers. Several screens consume synthetic values or silently fall back. |
| C-02 API gateway / identity boundary | `PARTIAL` | FastAPI `/api/v1`, JWT helpers, `routers/deps.py`; stricter auth is used for gold-loan and integration routers. | Ordinary routers use `get_current_tenant_and_user`, which permits demo fallback and does not verify membership when `X-Tenant-ID` selects a tenant. Replace fallback outside isolated demo mode; test every endpoint and role. |
| C-03 Case management | `PARTIAL` | Case CRUD/list/detail and `CaseService` state transitions; tenant filters on case queries. | Authorization and tenant-context flaws remain; no branch scope; no pagination; `CaseUpdate` not used; case number is random and not protected by unique constraint; status/decision preconditions are incomplete. |
| C-04 Evidence ingestion | `PARTIAL` | Local file storage, extension/size checks, SHA-256 metadata, tenant/case checks, download route. | Limit is checked after entire upload is read into memory; extension only, no content sniffing/AV; checksum is not revalidated on download; local disk is not object storage; transaction/file cleanup, retention, malware scanning, and immutable versions absent. |
| C-05 Validation / rules engine; R-FIN-01, R-TEN-02, R-EVID-03, R-POL-04 | `PARTIAL` | `ValidationService` persists four deterministic findings and updates case state. | `rule_version` is recorded but does not select executable version; rules are hardcoded; R-EVID-03 checks presence, not checksum integrity; R-POL-04 is a name-length check yet says registry/sanctions verified; warning does not block review; findings are deleted/replaced on rerun. |
| C-06 Decision records / maker-checker | `PARTIAL` | Generic decision API, approver role check, creator self-approval guard; gold-loan approval gate is deliberately closed. | Generic action does not require a review-ready case or passed validation; role coverage is uneven; gold approval always returns conflict until verified inputs are available; no delegated limits or durable loan decision ledger. |
| C-07 Audit/event history | `PARTIAL` | Hash-linked `AuditEvent`, list/verify/export routes; case/evidence/validation/decision and some gold events emit records. | Verifier only checks `prev_hash` links and does not recompute each event digest; append-only is not enforced at the database boundary; not all changes are audited; concurrency/order and canonical serialization are unresolved. |
| C-08 Integration adapters | `MOCKED` | Ten adapters and a registry, mode/status controls, failure injection; limited Razorpay sandbox/test API use. | Nine providers do not have production clients; no contracts/credentials/provider certification; modes are process-local. Test mode is not production completion. |
| C-09 Database / protected storage | `PARTIAL` | SQLAlchemy models and SQLite/PostgreSQL URL support; local evidence filesystem. | No migration scripts were found; startup calls `create_all`; no S3/private object store, DB row-level security, backup/restore evidence, tenant/branch constraints, or financial ledger schema. |
| C-10 Operations / governance | `PARTIAL` | `/system/health`, request timing/correlation response headers, deployment notes and Docker files. | Health leaks underlying DB exception text; no metrics/tracing/alerting/incident or job recovery; no backup/restore test; Docker uses development-oriented defaults; no CI workflow files found in the nested repository. |
| Multi-tenant SaaS / RBAC | `PARTIAL` | Tenant and membership entities; multiple query filters; `require_workspace_admin` used on integration controls. | No branch entity or branch-level scope. Legacy dependency accepts unverified tenant header and falls back to a seeded user. Most general routes do not enforce the documented role matrix. |
| Team workspace | `PARTIAL` | List/invite APIs and role fields. | Invitation creates/uses accounts with a fixed bootstrap password rather than an invitation/credential activation flow; role values are not comprehensively validated; no branch assignment or membership administration lifecycle. |
| Billing / subscriptions | `MOCKED` | Subscription row and usage queries exist. | Fixed demonstration plan, invoice list, storage fallback, renewal date, and baseline counts; no billing provider, invoice reconciliation, entitlement enforcement, or subscription lifecycle. |
| Monitoring, background jobs, deployment | `MISSING` | One synchronous health route, Dockerfile/Compose and prose deployment guide. | No scheduler/queue/outbox, operational dashboards, alert rules, CI/CD, deployment verification, backup execution, restore drill, or recovery objectives. |

## Gold-loan increments (existing IDs retained)

| Increment | Existing requirement terminology | Primary status | Evidence and incomplete acceptance |
|---|---|---|---|
| I-0 | Platform foundation; tenant isolation; typed `/api/v1`; audit chaining | `PARTIAL` | FastAPI, SQLAlchemy, JWT, tenant filters and audit hash code exist. No complete endpoint isolation guarantee, migrations, external immutable audit store, or end-to-end acceptance. |
| I-1 | Customer, consent, KYC; Aadhaar/PAN/CKYC; bureau; AML/PEP | `PARTIAL` | Customer/application/consent records persist. Identity, bureau, and screening adapters are synthetic; API stores only masked attempt data for the workflow simulator; no production provider result. |
| I-2 | Gold assay/device gateway; signed readings; calibration; replay | `MOCKED` | An HMAC-based simulator and nonce set exist. Hardcoded demo devices and ephemeral process secret do not authenticate a physical gateway. Intake/valuation accept staff-supplied weights and purity as simulated estimates. No persistent device enrollment, trusted calibration record, or complete multi-reading assay session. |
| I-3 | Gold valuation, eligibility; rate feed; policy; KFS | `PARTIAL` | Integer paise/milligram calculation, trace, limits, and binding constraint exist. Rates use non-approved free sources or static fallback; scheme caps are caller-provided; policies/rates are not approved/effective-dated; results are explicitly simulated in persisted workflow. KFS adapter returns “not generated or signed.” |
| I-4 | Vault custody; dual control; disbursal; loan booking | `MOCKED` | Custody and payout logic simulate results in memory. User-supplied maker/checker IDs are not authenticated identities at those endpoint boundaries. No bank transfer, physical vault event, loan booking, reconciliation, or durable payout state. |
| I-5 | Servicing, interest accrual, repayment waterfall, payment gateway | `PARTIAL` | Arithmetic functions exist. Razorpay test-mode order/payment API calls and payment order persistence/idempotency are present. No live payment collection, provider webhook, posting to a durable loan ledger, reversal, settlement reconciliation, or loan-account balance. |
| I-6 | MTM, margin calls, DPD/NPA, auction and settlement | `PARTIAL` | Pure calculations and sample threshold logic exist; auction is explicitly simulated. No schedule, persisted loan/notice/NPA state, borrower notification, actual auction, settlement, or surplus refund. Values in code are not approved business policy by evidence available. |
| I-7 | Production hardening; safe integration modes; secrets and resilience | `PARTIAL` | Some adapters reject providerless production use; production gate and failure simulation exist. Some production-mode behavior is not consistently guarded (notably the market-rate adapter); process-local state, route authorization gaps, weak defaults, and production operations controls remain. |

## Gold-loan business module trace

| Module / terminology in repository | Status | Key implementation and acceptance boundary |
|---|---|---|
| Customer records | `PARTIAL` | `GoldLoanCustomer` is persisted and linked to applications; optional external reference reuse is tenant-scoped. No customer lifecycle/deduplication, branch scope, or provider identity. |
| Loan applications / origination | `PARTIAL` | Gold Loan `Case` plus `GoldLoanApplication`, workflow events, consent, collateral and valuation snapshots. It is not a complete loan account lifecycle. |
| Consent | `PARTIAL` | Version, purpose, capture method, actor and accepted flag persist. No customer-captured evidence, consent withdrawal/revocation workflow, or approved wording evidence. |
| KYC / identity / screening / bureau | `MOCKED` | Synthetic adapters; no production provider invocation. KYC simulation remains indeterminate and approval gate prevents passing simulated KYC. |
| Gold inventory / assay | `MOCKED` | Manual intake estimates and simulated assay record; no trusted instrument-originated appraisal. |
| Valuation / eligibility | `PARTIAL` | Deterministic calculator; inputs and rate can be non-authoritative and manual; persisted snapshots are marked simulated. |
| Underwriting / decisions | `PARTIAL` | Generic case decision is implemented; gold decision records only refer/reject and blocks approval while inputs are unverified. |
| Documents / e-sign / e-stamp | `MOCKED` | Adapter explicitly reports that no KFS/document/signature is created. |
| Vault custody / packet tracking | `MOCKED` | In-memory simulator explicitly says no physical seal/release occurred. |
| Disbursal / booking | `MOCKED` | In-memory bank payout result; production client unavailable. No loan account created or ledger posted. |
| Repayment / payment | `PARTIAL` | Test-mode Razorpay order create and server-side verification; does not update loan ledger. |
| Servicing / MTM / collections | `PARTIAL` | Stateless calculations; arbitrary caller supplies loan/outstanding/collateral data. |
| Auction / recovery | `MOCKED` | Illustrative bid and refund calculation; no auction or settlement. |
| Audit / events | `PARTIAL` | Some gold actions persist workflow events and write global audit events. Full lifecycle coverage, immutable history and re-verifiable digests unproven. |

## Source evidence and missing specifications

Inspected existing references include `docs/implementation/REQUIREMENT_TRACEABILITY_MATRIX_I0_I7.md`, `docs/implementation/AURA_GOLD_LOAN_RECONCILIATION_AUDIT.md`, `docs/implementation/GOLD_LOAN_SAAS_TODO.md`, `docs/adr/ADR-001-STACK-RECONCILIATION-MODULAR-FASTAPI.md`, and top-level `README.md`, `ARCHITECTURE.md`, `API.md`, `DATABASE.md`, `SECURITY.md`, `TESTING.md`, `DEPLOYMENT.md`.

Those files preserve terminology and IDs but some are stale or contain contradictory completion claims. The gold-loan master prompt and primary requirements sets referred to by these reports were not found in the repository or inspected ZIP inventory. Obtain and approve the source baseline before treating omitted requirements, acceptance thresholds, policy values, or regulatory references as authoritative.
