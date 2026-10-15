# AURA REST API Specification (`/api/v1`)

All endpoints are versioned, typed, and enforce multi-tenant isolation. Interactive OpenAPI / Swagger UI is available at `http://localhost:8000/api/v1/docs`.

---

## 1. Authentication & Tenant Identity

### `POST /api/v1/auth/register`
Provisions a new tenant organization and owner account.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "Jordan Davies",
    "organization_name": "Northstar Bank"
  }
  ```
- **Response**: JWT access token, user profile, and tenant metadata.

### `POST /api/v1/auth/login`
Authenticates user and returns tenant-scoped JWT Bearer token.

### `GET /api/v1/auth/me`
Retrieves currently authenticated user and active tenant context.

---

## 2. Case Management (`C-03`)

### `GET /api/v1/cases/`
Lists authorized cases for the active tenant.
- **Query Parameters**:
  - `q`: Search term for case number, customer name, or facility type.
  - `status`: Filter by state (`IN_VALIDATION`, `READY_FOR_REVIEW`, `APPROVED`, etc.).

### `POST /api/v1/cases/`
Creates a new case and records an append-only audit event.
- **Request Body**:
  ```json
  {
    "customer_name": "Northbridge Equipment Ltd",
    "requested_amount": 250000.0,
    "tenure_months": 12,
    "purpose": "Machinery purchase",
    "product_type": "Asset finance"
  }
  ```

### `GET /api/v1/cases/{case_id}`
Retrieves full case details including attached evidence files, rule validation findings, and decision history.

### `POST /api/v1/cases/{case_id}/transition`
Executes an explicit state machine transition. Rejects invalid transitions with `400 Bad Request`.

---

## 3. Evidence Ingestion (`C-04`)

### `GET /api/v1/evidence/`
Lists evidence items for the current workspace.

### `POST /api/v1/evidence/upload`
Accepts multipart file upload, verifies file format (PDF, PNG, XLSX, DOCX up to 50MB), computes SHA-256 checksum, and stores the file in tenant-isolated storage.

### `GET /api/v1/evidence/{evidence_id}/download`
Provides authorized streaming download of the verified private document.

---

## 4. Deterministic Validation Engine (`C-05`)

### `POST /api/v1/validation/run`
Executes deterministic rule set `v1.0` against a case:
- `R-FIN-01`: Amount boundary checks ($1,000 to $10,000,000).
- `R-TEN-02`: Facility tenure feasibility (1 to 60 months).
- `R-EVID-03`: Evidence completeness & cryptographic checksum presence.
- `R-POL-04`: Entity identity & sanctions policy screening.
Returns structured outcomes (`PASSED`, `FAILED`, `WARNING`) and updates case status.

---

## 5. Review & Decisions (`C-06`)

### `POST /api/v1/decisions/`
Records an authorized underwriting decision:
- **Outcomes**: `APPROVED`, `REJECTED`, `RETURNED_FOR_CORRECTION`, `ESCALATED`.
- **Maker-Checker Enforcement**: Verifies separation of duties between case submitter and decision approver.

---

## 6. Audit & Compliance (`C-07`)

### `GET /api/v1/audit/`
Retrieves chronological audit events with SHA-256 hash chains.

### `GET /api/v1/audit/verify`
Performs cryptographic chain verification over all tenant events. Returns `{ "is_valid": true, "tampered_count": 0 }`.

### `GET /api/v1/audit/export?format=csv`
Streams an immediate CSV or JSON compliance export for auditors.

---

## 7. Analytics & Dashboard

### `GET /api/v1/analytics/dashboard`
Returns live operational metrics: open cases, pending validations, awaiting decisions, open exceptions, SLA compliance percentage, rule pass rate, workflow state distribution, and 7-day trend series.

---

## 8. System Diagnostics

### `GET /api/v1/system/health`
Returns service liveness, PostgreSQL connectivity status, and version metadata.
