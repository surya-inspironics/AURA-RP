# ADR-001: Technology Stack Reconciliation and Modular Gold Loan Architecture

## Status
**APPROVED** — 15 October 2026

## Context
The AURUM repository currently operates with a production-grade **Next.js 16 (React 19, TypeScript)** frontend and an asynchronous **Python FastAPI + SQLAlchemy 2.0** backend with SQLite development and PostgreSQL cloud deployment.
The uploaded target specification (*AURA-Gold-Loan-Master-Prompt.md*) specifies a full-scale Gold Loan Loan Origination System (LOS) and Loan Management System (LMS) for the regulated Indian lending market, referencing Java 21 / Spring Boot / Spring Modulith, Kafka, Temporal, Keycloak, and a Go device gateway.

Building two parallel backends (FastAPI + Spring Boot) within the same repository would create duplicate domain logic, split maintenance overhead, introduce divergent data models, and compromise delivery integrity.

## Decision
We **preserve and extend the existing Next.js + FastAPI + SQLAlchemy foundation** into a modular Gold Loan LOS/LMS architecture:

1. **Frontend**: Preserve the existing AURUM Next.js UI, layouts, branding, typography, components, and interactions. Extend it with:
   - Dedicated **Integrations & Environment Settings** control centre.
   - **Gold Loan LOS Station** (device readings, XRF/weight assay, purity fineness, valuation & eligibility engine).
   - **Vault Custody & LMS Servicing** (dual-control packet sealing, disbursal order queue, repayment waterfall, mark-to-market LTV revaluation).

2. **Backend**: Implement the Gold Loan LOS/LMS as a modular subsystem under `backend/app/gold_loan/` with clear domain boundaries:
   - `integrations/`: Typed adapter architecture supporting three explicit runtime modes: `MOCK` (deterministic simulator), `SANDBOX` (provider test environment), and `PRODUCTION` (authorized live endpoints).
   - `models/`: Fixed-precision integer monetary (paise) and weight (milligram) models for customers, KYC, assay sessions, loan accounts, transactions, vault packets, and margin calls.
   - `services/`: Pure, deterministic calculation engine for gold valuation and RBI-compliant eligibility, dual-control custody, loan servicing (waterfall repayment and daily interest accrual), and collections.
   - `routers/`: RESTful endpoints for integration management, device gateway, assay, valuation, disbursal, repayment, and servicing.

3. **External Integrations & Safety**:
   - Provide typed adapters for all 10 external gold loan services:
     1. Payment Gateway (Borrower repayments — UPI/NetBanking/Cards)
     2. Disbursal / Core Banking (Money out — IMPS/NEFT/Bank payout)
     3. Identity Verification (Aadhaar eKYC, PAN, CKYC)
     4. Credit Bureau (CIBIL/Experian synthetic credit scoring)
     5. AML, PEP, and Sanctions Screening
     6. Gold Rate Feed (IBJA benchmark rates in paise/mg)
     7. Device Gateway (Signed XRF and legal-metrology scale readings)
     8. Document E-Sign and E-Stamp (KFS, pledge agreements)
     9. Multi-channel Notifications (SMS, Email, WhatsApp)
     10. E-Auction & Settlement
   - Strict production safety gate: Test-mode data is explicitly segregated (`is_test_mode=True`), simulated readings are rejected in live financial workflows, and production mode is locked behind deployment-level credentials.

## Consequences & Benefits
- **Zero throwaway work**: All existing case management, evidence storage, SHA-256 audit chaining, and analytics remain intact and operational.
- **Single Source of Truth**: Unified database schema and business logic prevent synchronization drift.
- **Fast Execution & Verification**: High-speed automated test execution with pytest and complete requirement-to-code traceability across Increments I-0 to I-7.
