from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.analytics_service import AnalyticsService
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])

@router.get("/dashboard")
def get_analytics_dashboard(
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    metrics = AnalyticsService.get_dashboard_metrics(db, tenant.id)
    return metrics
