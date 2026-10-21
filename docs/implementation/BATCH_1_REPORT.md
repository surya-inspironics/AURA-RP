# AURA Batch 1 Report — Stabilize the Existing Application

**Status:** Complete for Batch 1 acceptance scope; no Batch 2 work started.  
**Repository:** `C:\AURA\aura-product-implementation`  
**Branch before edits:** `develop`  
**Architecture preserved:** Next.js + FastAPI modular monolith per ADR-001.

## Worktree protection

The worktree was already dirty before Batch 1. It contained existing Gold Loan UI/API/backend integration changes, Docker and launch files, virtual-environment data, and the prior audit documents. Those unrelated existing changes were not discarded or reverted. The files changed in this batch were reviewed in the context of their existing work. No application database was deleted, migrated, or used by the tests. No dependencies were installed and no commit, push, or deployment was made.

The pre-edit tracked modifications included `app/globals.css`, `app/page.tsx`, `backend/app/gold_loan/integrations/gold_rate_adapter.py`, `backend/app/main.py`, `backend/app/models/entities.py`, `backend/app/routers/decisions.py`, `backend/app/routers/gold_loan.py`, `backend/app/routers/system.py`, `backend/app/services/decision_service.py`, `components/GoldLoanStationView.tsx`, `components/PaymentsView.tsx`, `docs/implementation/REPOSITORY_AUDIT.md`, `lib/api.ts`, and `next.config.mjs`. Existing untracked work included `.venv/`, `Dockerfile.backend`, `components/GoldLoanCalculator.tsx`, `components/GoldRateTicker.tsx`, `docker-compose.yml`, `docs/implementation/GOLD_LOAN_SAAS_TODO.md`, the six other audit reports, `start.bat`, and `start.sh`.

## Changes made

- Added a fail-closed pytest setup that selects a unique disposable SQLite database before application imports, isolates uploaded evidence storage, resets schema/seed data for every test, blocks unmocked external HTTP calls at known adapter boundaries, and cleans up its own temporary files.
- Added regression coverage for test DB separation and non-test DB rejection.
- Corrected the maker-checker test to use separate owner and approver identities. The service’s creator self-approval control was preserved.
- Corrected the stale gold-rate adapter name assertion. The adapter remains a free-source feed with static fallback, not a certified production integration.
- Added a production refusal to both providerless gold-rate read methods.
- Corrected the calculator to read the backend’s actual `limits_comparison_paise.COLLATERAL_LTV_LIMIT` field, tightened the TypeScript valuation response contract, and replaced dynamic string indexing with typed limit keys in the station view.
- Fixed an audit-chain ordering defect discovered by the isolated suite: chain append and verification now use hash links rather than non-unique timestamps. Added a same-timestamp regression.
- Added the `typecheck` package script and removed `typescript.ignoreBuildErrors` from Next configuration after the standalone type check passed.
- Updated the test baseline report with the Batch 1 evidence and unresolved quality gates.

## Four previously reported backend failures

| Failure | Root cause | Resolution |
|---|---|---|
| Maker-checker expected HTTP 201, got 400 | The test used the default fallback identity to create and approve the same case. The application correctly rejected self-approval. | Test now uses two distinct Northstar identities and verifies the approval route. The `DecisionService` maker-checker guard is unchanged. |
| Adapter name expected `Gold Rate Simulator`, got `Gold Rate Feed (Live)` | The assertion described an obsolete adapter name; current code declares the feed name and tries free sources before a static fallback. | Updated the assertion to the current adapter identity; no production certification is implied. |
| Duplicate `payment_orders.provider_payment_id` (`pay_test_api`) | Tests were writing to a persistent configured database across invocations. The unique constraint correctly rejected a repeated row. | Each test invocation now uses a new disposable SQLite file and resets schema/data per test. The database uniqueness constraint remains intact. |
| Providerless gold-rate production guard | `set_mode(PRODUCTION)` could succeed and the adapter’s read methods could still return feed/fallback data despite no configured approved market-data provider. | `get_gold_rate` and `get_all_rates` now explicitly reject production-mode reads. |

## Test and quality-gate results

Commands ran from `C:\AURA\aura-product-implementation`:

| Exact command | Result |
|---|---|
| `pnpm test:backend` — run 1 | **Passed:** 27 passed, 11 warnings; exit code 0 (53.44s). |
| `pnpm test:backend` — run 2 | **Passed:** 27 passed, 11 warnings; exit code 0 (49.07s). |
| `pnpm typecheck` | **Passed:** `tsc --noEmit`, exit code 0. |
| `pnpm build` | **Passed:** Next.js 16.4.0 compiled, ran TypeScript validation, generated routes, exit code 0. |

During page-data collection the build logged a Better Auth warning that its base URL is unset and a `BetterAuthError` stating that the default secret is in use; the build nevertheless exited 0. These messages were not suppressed or represented as successful production configuration. No lint, CI, browser E2E, provider contract, or deployment check was run.

## Database and network safety

- A test database is generated under the operating system temporary directory with a unique `aura_test_` SQLite filename. Any externally preconfigured `AURA_TEST_DATABASE_URL` is rejected; the generated URL is validated as a new temporary SQLite file, separate from the environment-configured application SQLite DB.
- The fixture sets `DATABASE_URL` before importing the app, then drops and recreates only the isolated test schema before each test. It redirects evidence uploads into temporary storage and cleans up its database/storage after pytest exits.
- `httpx.get` and the payment adapter’s imported `urlopen` are blocked unless tests replace the adapter boundary. Gold-rate tests receive explicit static fallback fixture values. Payment tests use their own provider-boundary fakes.
- No live gold-rate or payment provider calls were observed in the two passing full-suite runs.

## Remaining blockers and limitations

- Login-issued JWTs include a tenant ID, while the legacy dependency can default the role to `owner` when that tenant claim is present. The maker-checker regression uses sub-only signed test tokens to exercise membership-role resolution; this Batch 1 did not change authentication or tenant authorization.
- Audit verification checks that the stored hash links form one chain, but does not recompute each hash from stored event contents. Concurrent audit append serialization is also not established.
- Gold-rate sourcing remains unapproved and uncertified; production reads now fail closed. No rate provider credentials/contracts were supplied or used.
- Better Auth URL/secret configuration, pre-existing FastAPI/Pydantic deprecation warnings, absent lint/CI/E2E gates, provider certification, migration strategy, backup/restore, and production recovery remain unresolved.
- Green tests/typecheck/build do not establish production readiness.

## Files touched by Batch 1

- `backend/tests/conftest.py` (created)
- `backend/tests/test_backend.py`
- `backend/tests/test_gold_loan_integrations.py`
- `backend/app/gold_loan/integrations/gold_rate_adapter.py`
- `backend/app/services/audit_service.py`
- `components/GoldLoanCalculator.tsx`
- `components/GoldLoanStationView.tsx`
- `lib/api.ts`
- `next.config.mjs`
- `package.json`
- `docs/implementation/TEST_COVERAGE_AND_BASELINE.md`
- `docs/implementation/BATCH_1_REPORT.md` (created)

The worktree still contains the unrelated pre-existing changes observed before this batch. `next-env.d.ts` was restored after the build’s generated update.

## Next batch recommendation

Do not treat Batch 1 as authorization to implement later business flows. Review this report first. The next narrowly scoped engineering batch should address the login-token tenant/role resolution defect with explicit endpoint authorization tests, after approval, without changing the existing UI.
