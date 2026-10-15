# AURUM — Enterprise Evidence Intake, Validation & Decision Traceability

> **Development-Stage Multi-Tenant SaaS Implementation**
> Built with Next.js 16, React 19, TypeScript, and a high-performance Python FastAPI backend.

---

## 1. System Overview

AURUM is a development implementation of an evidence intake and decision-traceability platform. Some general SaaS workflows are backed by the API and database; the gold-loan workflows are currently development simulators and are not production-ready.

- **Frontend**: Next.js 16.4 (App Router), React 19, TypeScript 5.7, Tailwind CSS 4, Lucide Icons. The existing brand identity, typography, visual hierarchy, and UX design have been preserved intact.
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT, Bcrypt, Asyncpg / Psycopg2.
- **Persistence**: Multi-tenant PostgreSQL (Neon / AWS RDS) with local SQLite fallback for seamless development.
- **Security**: General SaaS routes include tenant and role controls, private file storage, and audit logging. Gold-loan and integration routes require authentication, but tenant-scoped persistence, full authorization coverage, provider integrations, and complete audit records remain outstanding. See the [implementation traceability matrix](./docs/implementation/REQUIREMENT_TRACEABILITY_MATRIX_I0_I7.md).

---

## 2. Key Modules & Features

1. **Operational Overview & KPI Dashboard**
   - Live aggregated metrics: Total cases, open cases, pending validation, awaiting decision, open exceptions.
   - Real-time SLA compliance tracking and average turnaround time.
   - Interactive sparkline trendlines and operational conversion funnel.
   - Visual breakdown of cases by workflow stage.

2. **Case Lifecycle Management (`C-03`)**
   - Full state machine: `DRAFT` → `IN_VALIDATION` → `READY_FOR_REVIEW` → `APPROVED` / `REJECTED` / `EXCEPTION_RAISED` / `AWAITING_EVIDENCE`.
   - Priority levels, SLA deadlines, multi-field search, and status filters.
   - Interactive Case Detail Drawer showing real-time timeline, attached documents, and decision history.

3. **Secure Evidence Ingestion (`C-04`)**
   - File uploads with MIME validation, 50MB boundary, and SHA-256 checksum computation.
   - Tenant-isolated private object storage.
   - Secure download endpoints with access validation.

4. **Deterministic Validation Engine (`C-05`)**
   - Versioned rule sets (`v1.0`) enforcing financial amount limits (`R-FIN-01`), tenure boundaries (`R-TEN-02`), evidence completeness & checksum integrity (`R-EVID-03`), and entity sanctions screening (`R-POL-04`).
   - Granular findings reporting (`PASSED`, `FAILED`, `WARNING`).

5. **Maker-Checker Review & Decisions (`C-06`)**
   - Separation-of-duties enforcement: Case creators cannot approve their own submissions without dual-control review.
   - Timestamped decision recording with rationale and reviewer identity.

6. **Tamper-Evident Cryptographic Audit History (`C-07`)**
   - Append-only audit log with SHA-256 hash chaining (`current_hash = SHA256(prev_hash + ...)`).
   - In-app integrity verification endpoint (`GET /api/v1/audit/verify`).
   - One-click CSV and JSON export for regulatory compliance.

7. **Team & Multi-Tenant Administration**
   - Organization switching, member directory, and invitation workflows.
   - RBAC roles: Owner, Admin, Manager, Reviewer, Approver, Analyst, Auditor.

8. **Billing & Plan Management**
   - Tiered subscriptions (Enterprise plan baseline: $2,400/month).
   - Usage meters: cases created, storage consumed, and seat utilization against quotas.

---

## 3. Quick Start

### Prerequisites
- Node.js >= 20.x
- Python >= 3.11
- pnpm >= 9.x

### Starting the Application

1. **Install Frontend Dependencies**:
   ```bash
   pnpm install
   ```

2. **Start the Python FastAPI Backend** (runs on port `8000`):
   ```bash
   pnpm dev:backend
   # Or directly: python backend/run.py
   ```
   The backend auto-seeds the baseline enterprise organization (`Northstar Bank`) and initial test cases.

3. **Start the Next.js Frontend** (in a separate terminal, runs on port `3000`):
   ```bash
   pnpm dev
   ```

4. **Access the Application**:
   - Web App: [http://localhost:3000](http://localhost:3000)
   - Interactive API Docs (Swagger): [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

---

## 4. Running Automated Tests

Run the backend test suite:
```bash
pnpm test:backend
# Or directly: python -m pytest backend/tests -v
```

The current backend suite covers:
- Health check & readiness
- User registration & JWT authentication
- **Cross-tenant data isolation** (verifying Tenant B cannot access Tenant A records)
- Case lifecycle state machine transitions
- Evidence upload and SHA-256 checksum computation
- Deterministic policy validation engine execution
- Maker-checker decision approval workflow
- Cryptographic hash-chain audit log integrity
- Gold-loan calculation and simulator guard behavior. These tests do not certify end-to-end or production workflows.
