# AURA Controlled Pilot Origination Slice

**Status:** Implemented and verified as a controlled, non-production pilot workflow. This does not make AURA suitable for live lending or customer financial decisions.

## Scope and outcome

The approved first milestone was a staff pilot from gold-loan application intake through consent, recorded appraisal inputs, and a persisted valuation preview. No live money movement or provider-backed identity, assay, or rate feed was available or enabled.

The backend now:

- Requires an accepted consent record before simulated assay and valuation writes.
- Advances the application to `APPRAISAL_REVIEW` when a simulated appraisal input is recorded.
- Persists valuation results as simulated snapshots and forces their policy label to `UNAPPROVED-PILOT-PREVIEW`; a client cannot label its submitted values as an approved policy version.
- Rejects all gold-loan final decision outcomes with HTTP 409 until an approved underwriting policy, verified identity, trusted appraisal, and authorized gold-rate source are configured.
- Continues to label simulator readings as unauthenticated and valuation results as simulated.

The existing Next.js UI was not redesigned. Its gold-loan workspace now explains that final decision actions are unavailable pending the required controls.

## Requirement traceability

| Existing requirement ID | Status after this slice | Evidence boundary |
|---|---|---|
| I-1 — Customer, consent, KYC | `PARTIAL` | Tenant-scoped application and staff-attested consent persist; identity remains simulated and is not provider-verified. |
| I-2 — Gold assay/device gateway | `MOCKED` | Pilot assay inputs persist as simulated and explicitly unauthenticated; no physical device trust is established. |
| I-3 — Gold valuation, eligibility, rate feed and policy | `PARTIAL` | A calculation snapshot persists, but its policy label is forced to `UNAPPROVED-PILOT-PREVIEW` and its rate/input source is not approved. |
| I-4 — Custody, dual control, disbursal and booking | `MOCKED / BLOCKED` | No operational custody, payout, booking, or settlement behavior was added; final decisions remain disabled. |

## Verification

| Command | Result |
|---|---|
| `pnpm test:backend` (initial baseline, before this slice) | 38 passed, 11 warnings |
| `python -m pytest backend/tests/test_gold_loan_pilot_workflow.py -q` | 4 passed, 11 warnings |
| `pnpm test:backend` (post-change run 1) | 42 passed, 11 warnings |
| `pnpm test:backend` (post-change run 2) | 42 passed, 11 warnings |
| `pnpm typecheck` | Passed |
| `pnpm build` | Passed; build emitted Better Auth warnings because `BETTER_AUTH_URL`/base URL and a non-default `BETTER_AUTH_SECRET` are not configured |
| `git diff --check` | Reported pre-existing trailing whitespace in `docs/implementation/REPOSITORY_AUDIT.md` lines 3–4; this unrelated file was not changed for this slice |

Backend tests ran through the existing isolated temporary SQLite fixture. The fixture blocks unmocked external network access and supplies deterministic gold-rate test data. No live provider API was called.

## Files changed for this slice

- `backend/app/routers/gold_loan.py` — Consent gates, pilot appraisal status, non-claimable policy version, and disabled final decisions.
- `backend/tests/test_gold_loan_pilot_workflow.py` — Regression tests for consent ordering, simulated appraisal/valuation persistence, client policy-label spoofing, and disabled decision outcomes.
- `components/GoldLoanStationView.tsx` — Clear pilot and decision-availability disclosure.

The worktree already contained unrelated Batch 1/2 and other modified/untracked files before this slice. They were preserved and are not attributed to this report.

## Remaining blockers

- No approved consent wording/version or evidence-capture process was supplied. The existing consent record is a staff attestation, not proof of a provider-verified identity or a legally approved consent flow.
- KYC, physical assay/device trust, and gold-rate sourcing remain simulated or unapproved.
- LTV, eligibility, pricing, fees, and other underwriting rules remain unapproved; all valuation figures are previews only.
- Gold-loan final outcomes remain disabled. Disbursal, repayment posting, loan ledger, physical custody, release, and auction are not made operational by this slice.
- The broader audited blockers remain: branch-level authorization model, migration/recovery process, durable evidence controls, and production monitoring.

## Recommended next work

Obtain the approved Indian lending/underwriting and consent policy documents, identify the intended pilot's legal operating boundary, and approve provider/physical-appraisal procedures. Then implement only the provider-backed or explicitly staff-attested evidence path that can be tested without enabling disbursal. Keep decision and money-movement endpoints disabled until policy, identity, assay, rate provenance, and independent approval controls are verified.
