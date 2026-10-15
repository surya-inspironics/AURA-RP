# AURA Security Architecture & Controls

## 1. Multi-Tenant Isolation
- Strict server-side tenancy enforcement.
- Every API endpoint validates tenant membership and filters queries by `tenant_id`.
- Verified by automated cross-tenant security test (`test_cross_tenant_isolation`).

## 2. Least-Privilege Role-Based Access Control (RBAC)
Roles supported:
- **Owner**: Full workspace administrative authority and subscription billing controls.
- **Admin**: User and policy administration.
- **Reviewer**: Case review, evidence inspection, and validation execution.
- **Approver**: Maker-checker decision approval.
- **Analyst**: Case creation and evidence submission.
- **Auditor**: Read-only inspection of cases, evidence, and audit logs.

## 3. Maker-Checker Separation of Duties
To prevent fraudulent approvals, the user who creates a case cannot independently approve that case without dual-control verification recorded in the audit log.

## 4. Evidence Integrity & Object Security
- Maximum file size: 50MB.
- Permitted file extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.xlsx`, `.docx`, `.csv`.
- Cryptographic verification: SHA-256 computed immediately upon receipt and persisted with the record.
- Tenant-isolated storage directory structure: `{storage_dir}/{tenant_id}/{case_id}/{checksum}_{filename}`.
- Downloads served through authorized endpoints verifying caller tenant ownership.

## 5. Tamper-Evident Audit History
- Append-only database table.
- Cryptographic hash chaining ensures any modification to historical events invalidates subsequent hashes.
- Verification endpoint available for automated compliance audits.
