import json
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database.session import get_db
from backend.app.models.entities import AuditEvent
from backend.app.models.schemas import AuditEventResponse
from backend.app.services.audit_service import AuditService
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/audit", tags=["Audit & Event History"])

@router.get("/", response_model=List[AuditEventResponse])
def list_audit_events(
    limit: int = Query(50, le=200),
    action: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    query = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant.id)

    if action:
        query = query.filter(AuditEvent.action == action)
    if q:
        query = query.filter(AuditEvent.action.ilike(f"%{q}%") | AuditEvent.actor_name.ilike(f"%{q}%"))

    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()

    results = []
    for e in events:
        try:
            meta = json.loads(e.metadata_json) if e.metadata_json else {}
        except Exception:
            meta = {}
            
        results.append(
            AuditEventResponse(
                id=e.id,
                actor_name=e.actor_name,
                action=e.action,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                correlation_id=e.correlation_id,
                metadata=meta,
                prev_hash=e.prev_hash,
                current_hash=e.current_hash,
                created_at=e.created_at
            )
        )
    return results

@router.get("/verify")
def verify_audit_integrity(
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    report = AuditService.verify_integrity(db, tenant.id)
    return report

@router.get("/export")
def export_audit_log(
    format: str = Query("csv", regex="^(csv|json)$"),
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    events = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant.id).order_by(AuditEvent.created_at.asc()).all()

    if format == "json":
        data = [
            {
                "id": e.id,
                "timestamp": e.created_at.isoformat(),
                "actor": e.actor_name,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "prev_hash": e.prev_hash,
                "current_hash": e.current_hash,
                "metadata": json.loads(e.metadata_json or "{}")
            }
            for e in events
        ]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=aura_audit_log_{tenant.slug}.json"}
        )
    else:
        # Generate CSV
        lines = ["Event ID,Timestamp,Actor,Action,Entity Type,Entity ID,Current Hash,Prev Hash"]
        for e in events:
            lines.append(f'"{e.id}","{e.created_at.isoformat()}","{e.actor_name}","{e.action}","{e.entity_type}","{e.entity_id}","{e.current_hash}","{e.prev_hash}"')
        csv_content = "\n".join(lines)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=aura_audit_log_{tenant.slug}.csv"}
        )
