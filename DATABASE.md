# AURA Database Architecture & Schema Specification

## 1. Overview
The AURA multi-tenant database is engineered with PostgreSQL (Neon Serverless PostgreSQL for cloud production) and SQLAlchemy 2.0 ORM, featuring complete tenant isolation, foreign key constraints, indexes, and an append-only cryptographically chained audit log.

---

## 2. Entity Relational Diagram

```
┌──────────────────┐       1:N       ┌──────────────────┐
│     tenants      ├────────────────►│   memberships    │
└─────────┬────────┘                 └─────────▲────────┘
          │                                    │ N:1
          │ 1:N                      ┌─────────┴────────┐
          ├─────────────────────────►│      users       │
          │                          └──────────────────┘
          │ 1:N
          ├─────────────────────────►┌──────────────────┐
          │                          │      cases       │
          │                          └─────────┬────────┘
          │                                    │ 1:N
          │                          ┌─────────┼────────┐
          │                          │         │        │
          │                          ▼         ▼        ▼
          │                   ┌──────────┐┌─────────┐┌──────────┐
          │                   │ evidence ││ findings││decisions │
          │                   └──────────┘└─────────┘└──────────┘
          │ 1:N
          ├─────────────────────────►┌──────────────────┐
          │                          │   audit_events   │ (SHA-256 Hash Chain)
          │                          └──────────────────┘
          │ 1:1
          └─────────────────────────►┌──────────────────────┐
                                     │ tenant_subscriptions │
                                     └──────────────────────┘
```

---

## 3. Table Definitions & Constraints

### 3.1 `tenants`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Tenant UUID identifier |
| `name` | VARCHAR(255) | NOT NULL | Organization business name |
| `slug` | VARCHAR(100) | UNIQUE, INDEX | URL-safe workspace slug |
| `timezone` | VARCHAR(100) | DEFAULT 'UTC' | Organization timezone |
| `created_at`| TIMESTAMP | DEFAULT NOW() | Organization provisioning timestamp |

### 3.2 `users` & `memberships`
- `users`: Stores global user credentials with 12-round Bcrypt password hashing.
- `memberships`: Associates users with specific tenants under explicit roles: `owner`, `admin`, `manager`, `reviewer`, `approver`, `analyst`, `auditor`. Unique constraint on `(tenant_id, user_id)`.

### 3.3 `cases`
Enforces the core business lifecycle state machine:
- Statuses: `DRAFT`, `IN_VALIDATION`, `READY_FOR_REVIEW`, `APPROVED`, `REJECTED`, `EXCEPTION_RAISED`, `AWAITING_EVIDENCE`.
- Indexed on `tenant_id` and `case_number`.
- Foreign key to `tenants.id` with `ON DELETE CASCADE`.

### 3.4 `evidence_items`
- Tracks uploaded file metadata, SHA-256 cryptographic checksums, validation statuses, and tenant-isolated storage paths.

### 3.5 `validation_findings`
- Persists deterministic rule evaluation outputs (`PASSED`, `FAILED`, `WARNING`) linked to rule IDs (`R-FIN-01`, `R-TEN-02`, `R-EVID-03`, `R-POL-04`).

### 3.6 `decisions`
- Records authorized maker-checker outcomes (`APPROVED`, `REJECTED`, `RETURNED_FOR_CORRECTION`, `ESCALATED`) with signed reviewer rationale.

### 3.7 `audit_events` (Cryptographic Hash Chain)
- Every material transaction records `prev_hash` and `current_hash`.
- Formula:
  $$\text{current\_hash} = \text{SHA256}(\text{prev\_hash} : \text{tenant\_id} : \text{actor\_id} : \text{action} : \text{entity\_id} : \text{timestamp} : \text{metadata})$$
- Guaranteed append-only; historical changes break the hash chain and trigger verification alerts.

### 3.8 `tenant_subscriptions` & `invoices`
- Enforces multi-tenant resource limits (cases limit, storage limit in MB, seat quota).
