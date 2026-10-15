from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Tenant, User, Membership, Case, EvidenceItem, RuleSetVersion,
    ValidationFinding, Decision, AuditEvent, TenantSubscription, ExceptionItem
)
from backend.app.core.security import hash_password
from backend.app.services.audit_service import AuditService

def seed_initial_data(db: Session):
    existing_tenant = db.query(Tenant).filter(Tenant.slug == "northstar-bank").first()
    if existing_tenant:
        return

    now = datetime.now(timezone.utc)
    
    # 1. Create Primary Tenant: Northstar Bank
    tenant = Tenant(
        name="Northstar Bank",
        slug="northstar-bank",
        timezone="Europe/London (GMT+1)",
        created_at=now - timedelta(days=30)
    )
    db.add(tenant)
    db.flush()

    # 2. Create Users & Memberships
    users_data = [
        ("Jordan Davies", "jordan.davies@northstar.bank", "owner", "JD"),
        ("Maya Chen", "maya.chen@northstar.bank", "reviewer", "MC"),
        ("Samir Patel", "samir.patel@northstar.bank", "reviewer", "SP"),
        ("Alicia Rossi", "alicia.rossi@northstar.bank", "approver", "AR"),
        ("James Okafor", "j.okafor@northstar.bank", "analyst", "JO")
    ]

    users_map = {}
    for name, email, role, initials in users_data:
        u = User(
            email=email,
            hashed_password=hash_password("AuraSecure2026!"),
            full_name=name,
            avatar_initials=initials,
            is_active=True,
            created_at=now - timedelta(days=25)
        )
        db.add(u)
        db.flush()
        users_map[initials] = u

        mem = Membership(
            tenant_id=tenant.id,
            user_id=u.id,
            role=role,
            created_at=now - timedelta(days=25)
        )
        db.add(mem)

    # 3. Create RuleSetVersion
    rule_set = RuleSetVersion(
        version="v1.0",
        name="Enterprise Commercial & Asset Underwriting Rules",
        description="Standard AURA validation suite for commercial lending, asset finance and instrument-backed facilities.",
        rules_json='{"rules": ["R-FIN-01", "R-TEN-02", "R-EVID-03", "R-POL-04"]}',
        is_active=True,
        effective_date=now - timedelta(days=60),
        created_at=now - timedelta(days=60)
    )
    db.add(rule_set)
    db.flush()

    # 4. Create Initial Cases
    cases_data = [
        ("AUR-2026-01842", "Northbridge Equipment Ltd", "Asset finance", 250000.0, 12, "Heavy machinery procurement", "IN_VALIDATION", "MEDIUM", "M. Chen", "MC", 2, 12),
        ("AUR-2026-01839", "Lattice Works GmbH", "Commercial lending", 420000.0, 24, "Working capital facility", "READY_FOR_REVIEW", "HIGH", "S. Patel", "SP", 5, 18),
        ("AUR-2026-01837", "Meridian Field Services", "Instrument-backed", 180000.0, 6, "Receivables advance", "EXCEPTION_RAISED", "URGENT", "A. Rossi", "AR", 27, 9),
        ("AUR-2026-01831", "Harborline Logistics", "Asset finance", 310000.0, 18, "Fleet lease financing", "AWAITING_EVIDENCE", "LOW", "J. Okafor", "JO", 31, 6)
    ]

    for c_num, c_name, p_type, req_amt, tenure, purpose, status, priority, o_name, o_init, hrs_ago, f_count in cases_data:
        c = Case(
            tenant_id=tenant.id,
            case_number=c_num,
            customer_name=c_name,
            product_type=p_type,
            requested_amount=req_amt,
            tenure_months=tenure,
            purpose=purpose,
            status=status,
            priority=priority,
            owner_name=o_name,
            owner_initials=o_init,
            sla_hours=48,
            sla_due_at=now + timedelta(hours=36),
            created_by=users_map[o_init].id,
            created_at=now - timedelta(hours=hrs_ago),
            updated_at=now - timedelta(hours=hrs_ago)
        )
        db.add(c)
        db.flush()

        # Add initial evidence item
        evidence = EvidenceItem(
            tenant_id=tenant.id,
            case_id=c.id,
            file_name=f"Financial_Statements_{c_num}.pdf",
            file_type="Document",
            file_size_bytes=4200000,
            storage_path=f"storage/evidence/{tenant.id}/{c.id}/init_doc.pdf",
            sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            validation_status="VALIDATED",
            uploaded_by_id=users_map[o_init].id,
            uploaded_by_name=o_name,
            created_at=now - timedelta(hours=hrs_ago)
        )
        db.add(evidence)

        # Record AuditEvent with cryptographic hash
        AuditService.record_event(
            db=db,
            tenant_id=tenant.id,
            action="case.created",
            entity_type="case",
            entity_id=c.id,
            actor_id=users_map[o_init].id,
            actor_name=o_name,
            metadata={"case_number": c_num, "amount": req_amt}
        )

    # 5. Create Tenant Subscription
    sub = TenantSubscription(
        tenant_id=tenant.id,
        plan_name="Enterprise",
        monthly_price=2400.0,
        cases_limit=100,
        storage_limit_mb=102400,
        seats_limit=25,
        status="active",
        current_period_end=now + timedelta(days=17)
    )
    db.add(sub)
    db.commit()
