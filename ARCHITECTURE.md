# AURA Architecture Specification

## 1. Architectural Principles

AURA is designed as a decoupled enterprise application combining:
1. **Presentation Layer**: Next.js 16 (App Router), React 19, TypeScript with client-side optimistic caching and server-side route rewrites.
2. **Business & Gateway Layer**: Python 3.11 with FastAPI providing an asynchronous, typed REST API (`/api/v1`).
3. **Data Access & Persistence Layer**: SQLAlchemy 2.0 ORM with PostgreSQL (Neon) and SQLite local fallback.
4. **Storage Layer**: Tenant-scoped private file storage with SHA-256 cryptographic hashing.
5. **Security & Audit Boundary**: Cryptographically chained audit event log, JWT Bearer authentication, and row-level tenant scoping.

```
┌─────────────────────────────────────────────────────────────┐
│                 AURA Next.js Frontend                       │
│  (Overview Dashboard, Case Management, Evidence Inbox,     │
│   Team Workspace, Billing, Audit Trail, Settings)           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP /api/v1 (Next Rewrites)
┌──────────────────────────────▼──────────────────────────────┐
│                Python FastAPI Application                   │
│  ┌───────────────────────┐      ┌─────────────────────────┐ │
│  │   Auth & RBAC Gate    │      │  State Machine (Cases)  │ │
│  ├───────────────────────┤      ├─────────────────────────┤ │
│  │  Evidence Ingestion   │      │  Validation Engine v1.0 │ │
│  ├───────────────────────┤      ├─────────────────────────┤ │
│  │  Maker-Checker Review │      │  Crypto Hash Audit Log  │ │
│  └───────────────────────┘      └─────────────────────────┘ │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼───────────────┐
│     PostgreSQL / SQLite     ││    Private Object Storage    │
│ (Tenants, Users, Cases,     ││ (Tenant-Isolated Files,      │
│  Decisions, Audit Events)   ││  SHA-256 Verified Payloads)  │
└─────────────────────────────┘└──────────────────────────────┘
```

## 2. Multi-Tenancy Data Model

Every data query strictly enforces the `tenant_id` foreign key:
- `tenants` (id, name, slug, timezone, created_at)
- `users` (id, email, hashed_password, full_name, avatar_initials, is_active)
- `memberships` (id, tenant_id, user_id, role)
- `cases` (id, tenant_id, case_number, customer_name, requested_amount, status, priority, owner_name, sla_due_at)
- `evidence_items` (id, tenant_id, case_id, file_name, file_size_bytes, storage_path, sha256_checksum, validation_status)
- `validation_findings` (id, tenant_id, case_id, rule_id, rule_name, outcome, explanation, severity)
- `decisions` (id, tenant_id, case_id, actor_id, actor_name, outcome, eligible_amount, interest_rate, rationale)
- `audit_events` (id, tenant_id, actor_id, actor_name, action, entity_type, entity_id, prev_hash, current_hash)
- `tenant_subscriptions` (id, tenant_id, plan_name, monthly_price, cases_limit, storage_limit_mb, seats_limit)

## 3. Case State Machine

```
   ┌───────────┐
   │   DRAFT   │
   └─────┬─────┘
         │ submit
   ┌─────▼───────────┐         resolve
   │  IN_VALIDATION  ├─────────────────────────┐
   └─────┬─────┬─────┘                         │
         │     │ validation fails              │
validation passes│  ┌─────────────────────┐    │
         │     └──►│  EXCEPTION_RAISED   ├─────┘
         │         └──────────┬──────────┘
   ┌─────▼─────────────┐      │ reject
   │ READY_FOR_REVIEW  │◄─────┘
   └─────┬─────────────┘
         │
    maker-checker approval
   ┌─────▼─────┐
   │ APPROVED  │ (or REJECTED)
   └───────────┘
```

## 4. Cryptographic Audit Chain

Each audit event record computes a SHA-256 digest:
$$\text{current\_hash} = \text{SHA256}(\text{prev\_hash} : \text{tenant\_id} : \text{actor\_id} : \text{action} : \text{entity\_id} : \text{timestamp} : \text{metadata})$$

Any modification to past events breaks the subsequent hashes, immediately detected by `AuditService.verify_integrity()`.
