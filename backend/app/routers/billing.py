from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.billing_service import BillingService
from backend.app.routers.deps import get_current_tenant_and_user, require_workspace_admin

router = APIRouter(prefix="/billing", tags=["Billing & Subscription"])

@router.get("/summary")
def get_billing_summary(
    ctx=Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    summary = BillingService.get_billing_summary(db, tenant.id)
    return summary
