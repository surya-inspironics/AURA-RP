# AURA Test Coverage and Baseline

**Audit date:** 21 October 2026  
**Run environment:** Windows; nested application repository `C:\AURA\aura-product-implementation`. Results reflect the current dirty worktree, not a clean commit.

## Initial audit baseline (pre-Batch 1)

| Exact command | Ran? | Outcome | Interpretation / limitation |
|---|---:|---|---|
| `pnpm --dir C:\AURA\aura-product-implementation test:backend` | Yes | **Failed:** 22 passed, 4 failed, 11 warnings; pytest summary reported 14.68 seconds. | Existing tests run against the application-configured SQLAlchemy engine, not a dedicated isolated test DB. The suite attempted live market-rate requests (one DNS failure and one HTTP 403 in logs). Do not treat this as a clean/side-effect-free baseline. |
| `pnpm --dir C:\AURA\aura-product-implementation build` | Yes | Exit code 0; Next.js 16.4.0 compiled and generated routes. Output explicitly says **“Skipping validation of types.”** Build logged Better Auth missing base URL/default-secret warnings. | Build success is not type-check or readiness evidence. This command regenerated tracked `next-env.d.ts`; that generated diff was restored. |
| `pnpm --dir C:\AURA\aura-product-implementation exec tsc --noEmit` | Yes | **Failed:** `components/GoldLoanCalculator.tsx(177,40) TS2339`: `limits_comparison_paise` does not exist on the inferred `summary` type. | Confirms the Next build concealed a TypeScript error via `next.config.mjs` `ignoreBuildErrors: true`. |
| `pnpm --dir C:\AURA\aura-product-implementation lint` | No | Not run. | No lint script is defined in `package.json`; no separate lint setup was discovered. |
| `pnpm --dir C:\AURA\aura-product-implementation typecheck` | No | Not run. | No typecheck script is defined; direct `tsc --noEmit` was run instead. |
| `functions.runTests` with the four backend Python test files | Yes | “No tests found in the files.” | Runner did not discover this pytest suite; the repository’s own `test:backend` command was then run. |
| Security scan, dependency audit, browser E2E, migration, provider contract tests | No | Not run. | No supported configured commands/artifacts were identified; no dependencies were installed. |

## Backend test failures observed before stabilization

1. `backend/tests/test_backend.py::test_maker_checker_decision` — attempted approval returned HTTP 400, while the test expected HTTP 201. The test creates and approves the same case using the default identity; this conflicts with the creator self-approval control.
2. `backend/tests/test_gold_loan_integrations.py::test_registry_contains_all_10_adapters` — expected adapter name “Gold Rate Simulator”; current registry names it “Gold Rate Feed (Live)”.
3. `backend/tests/test_gold_loan_integrations.py::test_repayment_orders_are_persisted_and_tenant_scoped` — SQLite unique constraint failed for repeated `payment_orders.provider_payment_id` (`pay_test_api`) in the configured persistent DB.
4. `backend/tests/test_gold_loan_integrations.py::test_providerless_financial_flows_reject_production_mode` — production-mode guard expectation failed for a providerless adapter; the current gold-rate adapter does not consistently refuse production mode.

The test output also records attempts to refresh rates from external sources. These tests are therefore not hermetic. The current DB may have been changed by the test run: test fixtures call `Base.metadata.create_all()` and perform API writes using the configured engine, and no rollback/cleanup fixture was observed. No attempt was made to delete or restore any database records.

## Test inventory inspected

| Test file | Present coverage | Important untested surface |
|---|---|---|
| `backend/tests/test_backend.py` | Health, auth/demo context, registration/login, one case isolation scenario, case transition, upload checksum, validation, maker-checker, audit verify, analytics. | Complete route auth matrix; tenant-header membership; branches; all roles; evidence content/MIME/size streaming/tamper; rule version behavior; audit digest recomputation; pagination; concurrency. |
| `backend/tests/test_gold_loan_eligibility.py` | Single-item arithmetic, one binding limit, LTV upper flag, stone deduction greater than gross. | Negative gross/deductions, empty item set, zero/negative LTV and caps, precision/rounding boundaries, real approved rate/policy versions, property-based financial vectors. |
| `backend/tests/test_gold_loan_integrations.py` | Anonymous access to two routes, adapter count/name, production guard, mocked Razorpay calls/signature, repayment persistence/idempotency, disbursal simulator checks, device HMAC/replay behavior. | Actual provider contract, webhook, duplicate/unknown transaction recovery, all-route role/tenant authorization, payout persistence, concurrent idempotency, database isolation, live/test boundary for each provider. |
| `backend/tests/test_gold_loan_lifecycle.py` | Demonstrates adapters/calculators return simulation flags. | Complete UI-to-DB gold loan lifecycle, real providers, real assay, loan account/ledger, booking, servicing, collection, auction, customer notification. |

## Reproducibility and baseline gates at initial audit

- At the initial audit, scripts were `dev`, `dev:backend`, `test:backend`, `build`, and `start`; no lint/typecheck/e2e script was declared.
- `.env` was loaded by the Next build; its contents were not reproduced in this report. Runtime logs indicate Better Auth is not configured with an explicit base URL and non-default secret.
- The pre-Batch 1 backend command used the application-configured database and attempted external rate requests. See the Batch 1 results below for the isolated replacement.

## Batch 1 stabilization results

| Exact command | Runs | Outcome | Notes |
|---|---:|---|---|
| `pnpm test:backend` | 2 | **27 passed, 11 warnings** each; exit code 0 both times. | The test configuration selected a unique disposable SQLite file under the system temporary directory, reset schema/data per test, and cleaned the test DB and evidence storage after the run. |
| `pnpm typecheck` | 1 | **Passed** (`tsc --noEmit`, exit code 0). | Explicit script added; type check is independent from the build. |
| `pnpm build` | 1 | **Passed**; Next.js 16.4.0 compiled, ran TypeScript validation, and generated routes. | `typescript.ignoreBuildErrors` was removed. Better Auth logged a missing base URL warning and a default-secret `BetterAuthError` message during page-data collection; build exit code was still 0 and is not production-readiness evidence. |
| Lint / CI / browser E2E | 0 | Not run. | No lint or CI command was configured/discovered for this batch. |

### Resolution of the four initial backend failures

1. `test_maker_checker_decision`: the prior test used the same default fallback identity as maker and checker. The self-approval rejection in `DecisionService` was correct. The test now uses distinct Northstar owner and approver identities and checks the case decision through the endpoint. Sub-only signed test tokens are used so the current dependency resolves membership roles instead of defaulting to `owner` for login-issued tokens; that existing token-role inconsistency remains out of scope.
2. Adapter label: the implementation names the adapter `Gold Rate Feed (Live)` and currently attempts free rate sources before static fallback. The test expected the obsolete `Gold Rate Simulator` name; its expectation now matches the current implementation. This does not certify the feed or make it an approved production provider.
3. Duplicate `provider_payment_id` (`pay_test_api`): repeated test runs shared the configured application database, so persisted payment rows collided with the unique constraint. Tests now use a fresh disposable SQLite database and clean data per test/run. The uniqueness constraint and payment ID are unchanged.
4. Providerless rate production guard: the adapter could be switched to `PRODUCTION` but its rate methods could still return public-feed or fallback values. Both `get_gold_rate` and `get_all_rates` now reject production use until a market-data provider is configured.

### Additional deterministic defect found during stabilization

The isolated suite exposed intermittent invalid audit chains when SQLite events shared identical `created_at` values. Audit append and verification had relied on timestamp ordering. The service now finds the unique chain tail by hash links and verifies the linked chain without timestamp ordering; the regression sets all seeded event timestamps equal. This remains a structural chain check; the service does not recompute each event hash from its stored payload.

### Isolation and external-call controls

- `backend/tests/conftest.py` sets `DATABASE_URL` to a uniquely named temporary SQLite file before application modules load. An externally preconfigured `AURA_TEST_DATABASE_URL` is rejected; unsafe/non-SQLite paths also fail closed in the validation helper.
- The fixture drops and recreates only the isolated test schema for each test, seeds the test tenant, resets adapter simulator state, and redirects evidence storage to a temporary directory.
- Unmocked `httpx.get` and the payment adapter’s `urlopen` boundary raise an assertion. Gold-rate tests use explicit static fallback fixture values (`STATIC_FALLBACK`), while payment tests retain their explicit adapter-level fakes. These fixtures are test-only and do not represent certified provider responses.

### Remaining quality gates

- `package.json` now exposes `typecheck` and `test:backend`. The frontend typecheck and production build both passed separately.
- No lint or CI workflow was run; no applicable configured command was identified.
- Better Auth base URL/secret configuration messages remain. Do not treat green tests or build as production-readiness evidence.
- Authentication/tenant role resolution, provider certification, audit payload-hash recomputation, external provider contracts, migrations, backups, and production recovery remain separate reviewed work.
