# AURA Batch 2 — Authentication, Tenant Isolation and Role Authorization

**Status:** Implemented and verified against the repository's automated baseline. This is not a production-readiness assessment.

## Summary

The critical defect was the legacy tenant dependency's demo fallback: missing or invalid credentials could resolve the first database user, assign the `owner` role by default, and use a caller-supplied `X-Tenant-ID` without verifying that user's membership. Login also allowed inactive users and could produce a token without a valid tenant.

Protected FastAPI routes now require a valid bearer token, an active persisted user, a tenant claim bound to that user by a persisted membership, and a tenant context that matches the token. The role is read from that membership only; token role claims and request-supplied actor IDs do not grant permissions. The former dependency import name is retained as an alias to the strict resolver for compatibility.

## Authentication and session flow found

1. The visible Next.js sign-in and sign-up pages call the FastAPI methods in `lib/api.ts`; those forms do not use Better Auth.
2. FastAPI login verifies the password hash, active-user status and a persisted workspace membership. Registration creates the initial user, tenant and owner membership.
3. FastAPI issues a signed JWT with `sub`, `tenant_id`, `exp` and `iat`. Role is intentionally not an authority-bearing token claim.
4. The frontend stores the returned bearer token/profile in its existing local-storage session and sends the bearer token on protected API calls. No frontend session or visual changes were made.
5. The backend verifies the token signature, algorithm and required claims, then looks up the active user and exact `(user_id, token_tenant_id)` membership. A supplied `X-Tenant-ID` must match the token tenant.
6. Protected handlers receive the persisted membership role and tenant. Tenant-scoped reads and writes continue to filter on that tenant. Unauthorized credentials return `401`; authenticated requests without membership or permission return `403`; records outside the caller's tenant are not found.

Better Auth is also configured as a distinct `/api/auth/[...all]` route with server actions. The visible sign-in/sign-up flow uses FastAPI JWT instead; no active call path from those forms to Better Auth was found. The second identity path remains in the repository and should be reconciled through a separately reviewed architecture decision, not silently replaced here.

## Authorization matrix implemented

| Persisted membership role | Read tenant data | Persisted case/evidence/validation and gold-loan workflow mutations | Record decisions | Workspace settings, invitations and billing |
|---|---:|---:|---:|---:|
| `owner`, `admin` | Yes | Yes | Yes | Yes, except process-global integration controls |
| `approver` | Yes | Yes | Yes | No |
| `manager`, `reviewer`, `analyst` | Yes | Yes | No | No |
| `member`, `auditor` | Yes | No | No | No |

The existing code and UI provide role names but do not define a complete, authoritative permission matrix. This table is the implemented conservative guardrail, not a claim that the business has approved every permission. Business approval is still required, particularly for billing visibility and the exact operational capabilities of each role. No `owner` fallback exists. Owner role can be created only by the existing tenant-registration path; invite payloads cannot assign `owner`.

Decision creation requires an `owner`, `admin` or `approver`; the service receives the acting user from the validated context and retains its maker-checker check. Submitted actor IDs do not change that identity. Disbursal and vault actions now fail closed: the submitted first actor must match the authenticated user, and the endpoint returns `409` until a separate authenticated second-person approval flow exists.

## Endpoint review

| Route group | Access enforced |
|---|---|
| `/auth/register`, `/auth/login` | Public credential/registration endpoints; registration creates the initial owner membership |
| `/auth/me` | Strict bearer, active user and membership check |
| Cases | List/detail are tenant-bound reads; create and status transition require an operational role |
| Evidence | List/download are authenticated and tenant-scoped; upload requires an operational role and its case is tenant-bound |
| Validation | Findings are tenant-scoped reads; validation execution requires an operational role |
| Decisions | Listing is tenant-scoped; recording requires an approver role and the service enforces separation of duties |
| Audit and analytics | Authenticated tenant context; data queries use the authorized tenant |
| Team | Listing requires membership; invitations require workspace owner/admin and cannot elevate to owner |
| Billing | Summary requires workspace owner/admin and uses the authenticated tenant |
| System | Settings read requires membership; settings mutation requires owner/admin and uses tenant-bound settings; health is public and now logs only a generic database failure message |
| Integrations | Router requires membership; tenant workspaces cannot change process-global adapter modes or inject global failures (these operations return `403`) |
| Gold-loan | The private router requires membership; persisted application, case and repayment operations are tenant-scoped; application workflow writes and decisions apply role checks. Stateless calculator/helper endpoints require membership but do not persist tenant records. Only the separately registered live-rate endpoints are public. Disbursal and vault execution fail closed pending independently authenticated second actors. |

Branch isolation could not be enforced: the repository has no branch entity or persisted branch-membership/access model. `branch_reference` is a reference field, not an authorization boundary. This remains an explicit architecture/data-model blocker; no branch policy or schema was invented in this batch.

## Files changed for Batch 2

- `backend/app/core/security.py` — require and validate identity/tenant/time claims; reject malformed, expired and structurally invalid tokens.
- `backend/app/routers/deps.py` — remove demo/owner fallback; bind user, tenant and role to persisted records; reject tenant-header switching; add reusable role checks.
- `backend/app/routers/auth.py` — reject inactive or unassociated users at login and issue tokens without a role claim; protect `/auth/me`.
- `backend/app/models/schemas.py` — constrain invitation roles to existing non-owner roles.
- `backend/app/routers/cases.py`, `evidence.py`, `validation.py`, `decisions.py`, `team.py`, `billing.py`, `system.py`, `integrations.py`, `gold_loan.py` — apply role checks and/or fail closed where the previous identity or actor handling was unsafe.
- `backend/tests/test_backend.py`, `backend/tests/test_gold_loan_integrations.py` — adapt existing integration tests to authenticated API behavior; maker-checker coverage uses login-issued tokens.
- `backend/tests/test_security_authorization.py` — new login-based authorization and tenant-isolation regression coverage.

No frontend files, pages, navigation, styling or database schema were changed for Batch 2. The Batch 1 test harness remains responsible for temporary SQLite isolation, deterministic test data, fixture gold rates and blocking the identified HTTP/payment adapter network boundaries.

## Security regression tests

The new tests cover missing, malformed, expired and unbound tokens; login-issued token resolution; ignored role claims; missing/inactive user membership; tenant claim and `X-Tenant-ID` switching; cross-tenant case/evidence access; member privilege escalation; owner/admin operational compatibility; billing/payment isolation; authenticated approver identity and maker-checker separation; and spoofed disbursal/vault actor IDs. Existing registration, login, session-compatible bearer requests and protected API behavior also remain in the full suite.

## Verification results

| Command | Result |
|---|---|
| `pnpm test:backend` — run 1 | Passed: **37 passed**, 11 warnings, 94.18 seconds |
| `pnpm test:backend` — run 2 | Passed: **37 passed**, 11 warnings, 82.74 seconds |
| `pnpm typecheck` | Passed: `tsc --noEmit`, exit code 0 |
| `pnpm build` | Passed: `next build`, exit code 0; TypeScript phase completed |
| `git diff --check` | Reports two trailing-whitespace lines in the pre-existing modified `docs/implementation/REPOSITORY_AUDIT.md`; left untouched because it is unrelated existing work |

The frontend build logged Better Auth warnings that its base URL is unset and that its default secret is in use. The build still exited successfully; this does not validate the separate Better Auth path for deployment. The backend suite emits existing Pydantic, FastAPI and pytest deprecation warnings. No lint script is defined in `package.json`, so linting was not run. The test commands use the temporary SQLite database configured by `backend/tests/conftest.py`; neither run used the configured application database.

## Unresolved issues and required decisions

- **Branch authorization:** no branch identity/access model exists; branch-scoped authorization cannot be asserted or implemented safely from a text reference alone.
- **Membership activation and revocation:** the current schema has no membership active flag. Membership existence and `User.is_active` are checked; deleting a membership prevents further access. There is no token revocation/session table or `jti` mechanism, so already-issued tokens are not independently revocable before expiry.
- **Multiple workspaces:** login deterministically selects the earliest persisted membership. There is no tenant-switching UX; requests cannot change the token's tenant with a header.
- **Split identity:** Better Auth remains separately configured alongside FastAPI JWT. Select one supported identity/session authority in a reviewed architecture decision.
- **Permission policy:** the role matrix needs business-owner approval. Billing is owner/admin-only. Existing role names alone do not fully specify every permitted operation.
- **Invitations:** adding a new user is unavailable (`503`) until a verified account activation/invitation flow exists. The prior shared fixed-password path was removed.
- **Global integration settings:** mode changes and failure injection are deployment-scoped, so tenant admins receive `403`; define an appropriately privileged deployment control plane before enabling them.
- **Maker-checker workflows:** disbursal and vault sealing remain unavailable until separate authenticated checker/custodian approvals can be recorded and enforced.
- **Deployment configuration:** configure and validate Better Auth base URL and secret before using that route. Do not treat the successful Next.js build as evidence that the Better Auth runtime is production-ready.

The build regenerated `next-env.d.ts`; that generated-only change was restored to its pre-build contents. The worktree contains other pre-existing Batch 1 and user changes, which were preserved. No commit, deployment, UI redesign, new gold-loan workflow, migration or database operation against application data was performed.

## Recommendation

Before the next feature batch, review and approve the role matrix, choose the supported authentication authority, and define branch-membership and token-revocation requirements. Keep disbursal and vault actions disabled until real second-person authorization exists. This batch improves authentication and tenant checks but does not make AURA production-ready.
