# AURA Automated Verification & Test Strategy

## 1. Test Suite Summary
The platform contains automated test suites covering:
- **Tenant Isolation**: Verifying that tenant B cannot access, read, or modify tenant A cases or evidence.
- **State Machine Transitions**: Validating permitted and blocked transitions.
- **Evidence Checksums**: Validating SHA-256 calculation and payload storage.
- **Validation Engine**: Deterministic policy evaluation.
- **Maker-Checker Governance**: Verifying dual-control approval rules.
- **Audit Cryptographic Hash Chaining**: Verifying `prev_hash` to `current_hash` continuity.
- **Real-Time KPI Calculations**: Verifying dashboard metrics aggregation.

## 2. Running Automated Tests
```bash
# Run pytest backend test suite with verbose output
pnpm test:backend
```

All 10 tests execute and pass:
1. `test_system_health`: PASSED
2. `test_auth_me_default`: PASSED
3. `test_auth_register_and_login`: PASSED
4. `test_cross_tenant_isolation`: PASSED
5. `test_case_lifecycle_state_machine`: PASSED
6. `test_evidence_upload_and_checksum`: PASSED
7. `test_validation_engine_execution`: PASSED
8. `test_maker_checker_decision`: PASSED
9. `test_tamper_evident_audit_log_integrity`: PASSED
10. `test_analytics_dashboard_metrics`: PASSED
