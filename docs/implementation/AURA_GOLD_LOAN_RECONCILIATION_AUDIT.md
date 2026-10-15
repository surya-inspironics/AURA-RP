# AURUM Gold Loan LOS/LMS Reconciliation Audit

**Audit date:** 15 October 2026  
**Scope:** Existing AURUM repository, current implementation audit, supplied gold-loan master prompt, architecture/DFD diagrams, and eligibility-calculation reference.

## Executive verdict

The existing repository is a **Next.js frontend prototype**, while the supplied target is a substantially larger **Gold Loan Loan Origination System (LOS) and Loan Management System (LMS)**. The target is not implemented end to end. The current UI may be retained as a discovery shell, but it must not be represented as an operational lending platform.

**Release classification:** UI discovery prototype only.  
**Production readiness:** Not ready.  
**Primary risk:** implementing contradictory architecture and financial rules before the target specification is reconciled.

## 1. Technology-stack cross-verification

| Area | Existing repository | Gold-loan target | Finding |
|---|---|---|---|
| Frontend | Next.js 16 App Router, React, TypeScript | Nx, React, TypeScript, Tailwind, shadcn/ui, multiple workspaces/federation | Partial; current shell is reusable, federation/workspaces absent |
| Backend | None | Java 21, Spring Boot 3.3, Spring Modulith | Missing |
| Data | None | PostgreSQL | Missing |
| Messaging | None | Kafka/domain events/transactional outbox | Missing |
| Orchestration | None | Temporal | Missing |
| Identity | None | Keycloak/enterprise IAM | Missing |
| Device gateway | None | Go gateway for signed analyzer readings | Missing |
| Object storage | None | MinIO/private object storage or approved equivalent | Missing |
| Deployment | None | Docker/Kubernetes/AWS-oriented operations | Missing |
| Observability | None | Logs, metrics, traces, alerts and audit evidence | Missing |

### Architecture decision required

Do not implement Flask and Spring Boot duplicate business services. Create an architecture decision record before build-out. The recommended reconciliation is:

- Retain the existing Next.js frontend shell where useful.
- Add one Java/Spring Boot modular monolith as the authoritative business backend.
- Keep device ingestion isolated behind a Go gateway only if signed-device protocol needs a separate trust boundary.
- Start with Docker Compose and mocked integrations.
- Introduce Kafka, Temporal, federation and Kubernetes only after a vertical slice has verified need and delivery semantics.

## 2. Target module-flow coverage

The supplied target expands the earlier C-01–C-10 evidence product into a gold-loan LOS/LMS. Required flow:

`Customer intake → consent/KYC → case creation → gold item registration → signed assay → valuation → eligibility → underwriting → approval → documents/signature → custody → disbursal → servicing → collections → closure/auction → audit/export`

| Target capability | Current repository evidence | Status |
|---|---|---|
| Customer onboarding and consent | Static customer workspace only | Missing |
| KYC and verification | No identity or verification adapter | Missing |
| Gold item and assay session | No device or assay model | Missing |
| Instrument readings | No gateway, signatures, calibration or replay protection | Critical missing |
| Gold valuation and eligibility | No calculation engine | Critical missing |
| Underwriting and maker-checker approval | No decision service or authorization | Missing |
| Documents and signatures | No document generation/signing | Missing |
| Packet custody and dual control | No custody model or workflow | Missing |
| Payment/disbursal | No payment adapter or reconciliation | Missing |
| Loan servicing | No loan account, accrual or repayment engine | Missing |
| Collections, NPA and auction | No servicing/collections modules | Missing |
| Audit and exception management | Static audit display only | Prototype only |
| Policy/device administration | No rules or device administration | Missing |

## 3. Eligibility calculation reconciliation

The supplied references must be converted into one authoritative, versioned specification before implementation. The common calculation shape is:

$$W_{fine}=W_{net}\times\frac{P}{100}$$

$$V_{gold}=W_{fine}\times R_{approved}$$

$$L_{collateral}=V_{gold}\times LTV_{max}$$

$$L_{eligible}=\min(L_{collateral},L_{credit},L_{capacity},L_{product},L_{exposure})$$

The target must explicitly choose either a pure-gold convention or a 22K-equivalent convention. It must define gross weight, deductions, net eligible weight, purity/fineness units, price basis, LTV scheme, bullet-loan adjustments, rate source, paise/weight precision, rounding points, stale inputs and invalid inputs.

The proposed 85%, 80% and 75% LTV slabs remain **provisional** until compliance/product approval. They must not be encoded as production policy without an approved rule-set version.

The engine must return a complete calculation trace, all applicable limits, binding limit, rule versions, rounding details and blocking exceptions. It must be deterministic, pure and unit tested at slab boundaries and failure conditions.

## 4. Workflow and control requirements

The diagrams are not executable specifications until each transition defines:

- actor and authorization scope;
- source and destination state;
- preconditions and stage gates;
- database mutation and transaction boundary;
- emitted domain events and outbox behavior;
- audit evidence and correlation ID;
- failure outcome, retry and recovery behavior.

Required state machines include customer/consent, KYC, loan case, gold item, assay session, instrument reading, valuation, eligibility, underwriting, decision, pledge documents, custody packet, payment order, loan account, collections, exception and rule publication.

## 5. Critical security findings

1. Staff must not type or edit authoritative purity and weight values.
2. Readings must originate from a registered device through a trusted gateway.
3. The backend must verify device identity, certificate/key lifecycle, signatures, calibration validity, trusted capture timestamp, replay protection, duplicate protection and correlation IDs.
4. Offline device buffering must preserve ordering and integrity during synchronization.
5. Required XRF spot readings and consistency checks must be policy-controlled.
6. Overrides require dual control and a mandatory re-assay or approved exception path.
7. Simulator readings must be isolated, visibly marked and rejected by production workflows.
8. Evidence versions must be immutable and integrity-verifiable.

A frontend-generated device ID or simulated reading is not evidence of authenticity.

## 6. Missing engineering specifications

Before implementation, add approved specifications for:

- deterministic rules expression language, type system, sandbox, effective dates, rollback and maker-checker publication;
- transactional outbox, canonical event serialization, ordering, hash-chain canonicalization, key handling and recovery;
- integer monetary units, weight/fineness units and rounding rules;
- day-count convention, accrual timing, value dates, repayment waterfall, reversals and idempotent end-of-day processing;
- Aadhaar/PII masking, consent, retention, residency, access logging and privacy-safe observability;
- integration adapter contracts, timeouts, retries, status inquiries, reconciliation and failure injection;
- environments, migrations, secrets, network boundaries, recovery objectives and rollback;
- requirement-to-test-to-evidence traceability.

## 7. Recommended implementation sequence

1. Approve architecture decision and reconcile repository migration path.
2. Freeze the eligibility policy and unit conventions with compliance sign-off.
3. Build one modular Java vertical slice: customer, consent, case, evidence, assay stub, eligibility trace, decision and audit.
4. Add PostgreSQL schema, authorization/tenant model and immutable audit/outbox.
5. Add a signed-device gateway with a test device and negative security tests.
6. Add documents, custody and disbursal reconciliation.
7. Add servicing, collections, auction and closure workflows.
8. Add integrations, Kafka/Temporal where justified, observability and operations.
9. Expand frontend workspaces only as backed by verified APIs.
10. Gate release on functional, security, financial-calculation, resilience and operational evidence.

## Final conclusion

The current AURUM implementation is a credible visual foundation but has no verified gold-loan business execution path. The supplied target is materially broader than the existing evidence-intake prototype. The next safe step is specification reconciliation and a small end-to-end vertical slice—not a wholesale scaffold of all workspaces and infrastructure.

**Evidence basis:** existing repository audit, source requirements/architecture documents, gold-loan master-prompt review text, architecture/DFD references and eligibility-calculation reference.

**Verification caveat:** this audit verifies repository structure and specification alignment; it does not certify lending-policy compliance, device authenticity, financial correctness or production security.
