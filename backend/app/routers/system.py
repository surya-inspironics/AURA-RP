import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Optional
from backend.app.database.session import get_db
from backend.app.models.entities import TenantSettings, Tenant
from backend.app.routers.deps import get_current_tenant_and_user, require_workspace_admin

router = APIRouter(prefix="/system", tags=["System Operations & Health"])
logger = logging.getLogger(__name__)


class WorkspaceSettingsPayload(BaseModel):
    organization_name: Optional[str] = None
    timezone: Optional[str] = None
    default_case_owner: Optional[str] = None
    notification_email: Optional[str] = None
    sla_alert_hours: Optional[int] = None
    require_dual_approval: Optional[bool] = None


@router.get("/settings")
def get_workspace_settings(
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant.id).first()
    if not settings:
        settings = TenantSettings(
            tenant_id=tenant.id,
            organization_name=tenant.name,
            timezone="Asia/Kolkata (IST)",
            default_case_owner="Assign to team queue",
            sla_alert_hours=24,
            require_dual_approval=True,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return {
        "organization_name": settings.organization_name or tenant.name,
        "timezone": settings.timezone,
        "default_case_owner": settings.default_case_owner,
        "notification_email": settings.notification_email,
        "sla_alert_hours": settings.sla_alert_hours,
        "require_dual_approval": settings.require_dual_approval,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


@router.put("/settings")
def update_workspace_settings(
    payload: WorkspaceSettingsPayload,
    ctx=Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant.id).first()
    if not settings:
        settings = TenantSettings(tenant_id=tenant.id, organization_name=tenant.name)
        db.add(settings)

    if payload.organization_name is not None:
        settings.organization_name = payload.organization_name
        tenant_obj = db.query(Tenant).filter(Tenant.id == tenant.id).first()
        if tenant_obj:
            tenant_obj.name = payload.organization_name
    if payload.timezone is not None:
        settings.timezone = payload.timezone
    if payload.default_case_owner is not None:
        settings.default_case_owner = payload.default_case_owner
    if payload.notification_email is not None:
        settings.notification_email = payload.notification_email
    if payload.sla_alert_hours is not None:
        settings.sla_alert_hours = payload.sla_alert_hours
    if payload.require_dual_approval is not None:
        settings.require_dual_approval = payload.require_dual_approval

    settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(settings)
    return {"ok": True, "updated_at": settings.updated_at.isoformat()}


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Database health check failed")
        db_status = "unhealthy"

    return {
        "status": "operational" if db_status == "healthy" else "degraded",
        "service": "AURA Enterprise Backend",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
