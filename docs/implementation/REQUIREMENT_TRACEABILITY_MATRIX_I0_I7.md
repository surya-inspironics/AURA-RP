# AURUM Gold Loan SaaS: Requirement-to-Code Traceability Matrix (I-0 through I-7)

**Review Date:** 15 October 2026
**Review scope:** Source-code inspection; this is not a compliance certification or production-readiness assertion.
**Status key:** `PARTIAL` means some local calculation or UI exists, not that the complete requirement is implemented. `SIMULATED` means no provider, physical device, bank, or persistent financial ledger is involved. `NOT VERIFIED` means acceptance criteria have not been demonstrated end-to-end.

The previous status summary overstated implementation. Adapter-shaped classes and passing unit-level calculations do not prove provider integration, persistent records, authenticated identities, regulatory compliance, or completed lifecycle workflows. The gold-loan API currently exposes several in-memory development simulators. Do not use their outputs as lending decisions, verified KYC, physical custody evidence, payment confirmations, or signed documents.

---

## Traceability Summary Table

| Increment | Title | Current status | Evidence and principal blockers |
|---|---|---|---|
| **I-0** | Platform foundation | **PARTIAL — NOT VERIFIED END-TO-END** | Gold-loan routes now require a valid bearer token and tenant membership; integration controls require authentication, with mode/failure changes restricted to owner/admin. Gold-loan actions are still not wired through tenant-scoped persistence or audit records. |
| **I-1** | Customer, consent, KYC | **SIMULATED — PROVIDERS ABSENT** | PAN/Aadhaar/CKYC are local format simulators. Consent is not persisted; no identity provider is queried; downstream decision gating is absent. |
| **I-2** | Gold assay & device gateway | **SIMULATED — NOT AN AUTHENTICATED DEVICE FLOW** | A server-side HMAC simulator and nonce cache exist. One spot can be simulated; no physical gateway/public-key enrollment, persisted calibration evidence, three-spot check, or assay record is wired. |
| **I-3** | Credit, valuation, eligibility | **PARTIAL — SAMPLE INPUTS/RATES** | Integer calculation code exists. Gold rates are static simulator values; scheme values are caller-provided; case inputs, rule versions, evidence, and decisions are not persisted as a reconstructable decision. |
| **I-4** | Custody & disbursal | **SIMULATED — NO PHYSICAL OR BANK EVENT** | Custody and payout adapters are in-memory. No authenticated custodians, movement history, real payout provider, reconciliation, or durable ledger posting is wired. |
| **I-5** | Servicing & repayments | **PARTIAL — RAZORPAY TEST CHECKOUT ONLY** | Test-mode Razorpay order creation, hosted checkout, server-side signature/payment-status verification, tenant-scoped persisted order history, and database idempotency are wired. Live charges are blocked. There is no raw-body webhook flow, production payment client, value-dated loan ledger, reversal lifecycle, or restart recovery/reconciliation for an ambiguous provider timeout. |
| **I-6** | Collections, MTM & auctions | **SIMULATED — NO COLLECTIONS LIFECYCLE** | Static-rate calculations and illustrative auction values exist. No scheduler, policy configuration, persisted notices, real auction, settlement, or refund workflow is wired. |
| **I-7** | Production hardening | **INCOMPLETE — PRODUCTION BLOCKED** | Providerless production paths are now explicitly rejected for the simulator surfaces changed in this increment. Remaining adapters, authorization edge-case coverage, durable tenancy, credential rotation, and persistence need review and implementation. |

### Highest-priority defects found

1. The payout simulator returned `SETTLED` plus a fabricated UTR, and the UI claimed the core banking ledger was updated.
2. Sandbox KYC returned provider-shaped success; PAN responses included the full PAN.
3. The assay UI described manually supplied simulator values as authenticated device readings.
4. The KFS and custody flows claimed real signatures/sealing without providers or physical authorization.
5. Sample gold prices were named and described as an authoritative IBJA feed; auction simulation claimed settlement.
6. Razorpay credentials are environment-only. The repayment workflow now contacts Razorpay with server-side test credentials and verifies checkout signatures and provider payment status. Live charging, webhook reconciliation, and loan-ledger posting remain disabled.
7. Gold-loan and integration-control routes initially lacked authorization. They now enforce bearer authentication and tenant membership; regression tests verify anonymous requests are rejected (401). Valid-member, cross-tenant, and owner/admin authorization cases still need dedicated coverage, as do tenant-scoped gold-loan records and audit persistence.

---

## Detailed Increment Breakdown

### Increment I-0: Technical Foundation, Module Boundaries, Audit Chaining
- **Requirements**:
  - Multi-tenant data segregation.
  - Asynchronous typed REST API `/api/v1`.
  - Cryptographically chained SHA-256 audit log.
  - Evidence ingestion with SHA-256 digest validation.
- **Traceability**:
  - `backend/app/models/entities.py`: `Tenant`, `User`, `Membership`, `AuditEvent`, `EvidenceItem`.
  - `backend/app/services/audit_service.py`: `log_event()` and `verify_integrity()`.
  - `backend/tests/test_backend.py`: Cross-tenant leak tests pass with 404 isolation.

### Increment I-1: Customer Onboarding, Consent, KYC, Bureau & AML
- **Requirements**:
  - Customer intake with explicit consent timestamp.
  - Aadhaar eKYC with mandatory 12-digit masking (`XXXX-XXXX-1234`).
  - PAN format validation and algorithmic name matching.
  - Central KYC (CKYC) registry integration.
  - CIBIL/Experian bureau score lookup.
  - AML / OFAC sanctions and PEP screening with fuzzy scoring.
- **Traceability**:
  - `backend/app/gold_loan/integrations/identity_adapter.py`: `IdentityAdapter` (Aadhaar, PAN, CKYC).
  - `backend/app/gold_loan/integrations/credit_bureau_adapter.py`: `CreditBureauAdapter`.
  - `backend/app/gold_loan/integrations/screening_adapter.py`: `ScreeningAdapter`.

### Increment I-2: Gold Assay, Device Gateway, Signed Readings, Calibration
- **Requirements**:
  - Trusted device gateway with registered device identities (serial, model, calibration validity).
  - Cryptographic HMAC-SHA256 signature verification on XRF and legal-metrology precision balance readings.
  - Replay protection with nonce and timestamp check.
  - Staff prohibited from manual purity or gross weight override.
  - Clear `is_simulated: true` flagging; rejection in production financial workflows.
- **Traceability**:
  - `backend/app/gold_loan/integrations/device_gateway_adapter.py`: `DeviceGatewayAdapter`.
  - `backend/app/gold_loan/models/gold_loan_entities.py`: `DeviceReading`, `AssaySession`, `GoldPledgeItem`.

### Increment I-3: Gold Valuation, Eligibility Engine, KFS & Documents
- **Requirements**:
  - IBJA versioned gold rate feed in paise per milligram with staleness check (>24h).
  - Pure integer fixed-precision arithmetic (paise, mg, basis points).
  - Eligibility formula:
    $$W_{fine} = W_{net} \times \frac{P}{10000}$$
    $$V_{gold} = W_{fine} \times R_{approved}$$
    $$L_{collateral} = V_{gold} \times \frac{LTV_{max}}{100}$$
    $$L_{eligible} = \min(L_{collateral}, L_{credit}, L_{capacity}, L_{product}, L_{exposure})$$
  - Intermediate trace output and binding constraint identification.
  - Key Fact Statement (KFS) and pledge agreement generation with simulated e-sign / e-stamp.
- **Traceability**:
  - `backend/app/gold_loan/services/eligibility_engine.py`: `EligibilityEngine`.
  - `backend/app/gold_loan/integrations/gold_rate_adapter.py`: `GoldRateAdapter`.
  - `backend/app/gold_loan/integrations/document_signer_adapter.py`: `DocumentSignerAdapter`.

### Increment I-4: Vault Packet Custody, Dual Control & Loan Disbursal
- **Requirements**:
  - Dual-custody packet sealing with two authorized branch custodians.
  - Unique tamper-evident barcode generation.
  - Loan disbursal via separate payout adapter (Money Out: Bank IMPS/NEFT/Core Banking).
  - Maker-checker approval requirement before payment execution.
  - Idempotency key protection and duplicate disbursal prevention.
  - Loan account activation only after confirmed settlement.
- **Traceability**:
  - `backend/app/gold_loan/services/custody_service.py`: `CustodyService`.
  - `backend/app/gold_loan/integrations/disbursal_adapter.py`: `DisbursalAdapter`.
  - `backend/app/gold_loan/models/gold_loan_entities.py`: `VaultPacket`, `LoanAccount`, `LoanTransaction`.

### Increment I-5: Loan Servicing, Interest Accrual & Borrower Repayments

**Implemented in this increment:** Razorpay TEST-mode Orders API calls and hosted Checkout; authenticated tenant-scoped order history persisted in the application database; per-tenant idempotency keys; server-side checkout signature validation followed by provider payment-status and amount/currency verification. The browser receives only the public test key ID. No payment secret is sent to the frontend.

**Not implemented:** live-mode charging, provider webhooks, durable payment/loan ledger entries, settlement/reversal workflows, disbursement, or recovery automation after an ambiguous provider timeout. A `CAPTURED` result means captured in Razorpay's test environment only and does not activate or modify a loan account. The current order form accepts a loan reference; it does not prove the reference is a disbursed, payable loan.
- **Requirements**:
  - Daily interest accrual calculation.
  - Customer loan repayments (Money In: UPI / Payment Gateway).
  - HMAC-SHA256 webhook signature verification.
  - Idempotency protection against duplicate provider callbacks.
  - Exact repayment waterfall allocation: `Penalties -> Overdue Interest -> Current Interest -> Principal`.
  - Collateral unsealing & release upon full loan closure.
- **Traceability**:
  - `backend/app/gold_loan/services/loan_servicing_engine.py`: `LoanServicingEngine`.
  - `backend/app/gold_loan/integrations/payment_gateway_adapter.py`: `PaymentGatewayAdapter`.

### Increment I-6: Mark-to-Market LTV, Margin Calls & E-Auction Settlement
- **Requirements**:
  - Automated MTM LTV revaluation against updated gold benchmark rates.
  - Margin call notification generation when LTV exceeds trigger threshold (e.g. > 85%).
  - Delinquency and NPA tracking (90+ DPD).
  - E-auction integration with reserve price calculation and surplus distribution to borrower.
- **Traceability**:
  - `backend/app/gold_loan/services/collections_engine.py`: `CollectionsEngine`.
  - `backend/app/gold_loan/integrations/auction_adapter.py`: `AuctionAdapter`.
  - `backend/app/gold_loan/integrations/notification_adapter.py`: `NotificationAdapter`.

### Increment I-7: Production Readiness, Security & Environment Safety
- **Requirements**:
  - 3 typed modes: `MOCK`, `SANDBOX`, `PRODUCTION`.
  - Failure injection engine (timeout, invalid signature, duplicate callback, amount mismatch, upstream 500).
  - Restricted Integrations & Environment Settings control centre in UI.
  - Server-side secret protection: Secrets never leaked to browser.
  - Production guard: Production mode rejected without explicit environment configuration and credentials.
- **Traceability**:
  - `backend/app/gold_loan/integrations/base.py`: `BaseAdapter`.
  - `backend/app/gold_loan/integrations/registry.py`: `AdapterRegistry`.
  - `backend/app/routers/integrations.py`: REST control API.
  - `app/page.tsx`: UI Integrations Control Centre.
