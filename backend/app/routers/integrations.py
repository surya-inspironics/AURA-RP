from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from backend.app.gold_loan.integrations.base import IntegrationMode
from backend.app.gold_loan.integrations.registry import adapter_registry
from backend.app.routers.deps import require_authenticated_tenant_and_user, require_workspace_admin

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations & Environment"],
    dependencies=[Depends(require_authenticated_tenant_and_user)]
)

class ModeUpdateRequest(BaseModel):
    mode: IntegrationMode

class SimulateFailureRequest(BaseModel):
    scenario: Optional[str] = None  # timeout, invalid_signature, duplicate, mismatch, upstream_500, clear

@router.get("/")
def list_integrations():
    """
    Returns statuses of all 10 Gold Loan external integration adapters.
    Accessible to authorized team members. Secrets are never exposed.
    """
    return {
        "adapters": adapter_registry.get_all_statuses(),
        "environment": "development",
        "production_enabled": False
    }

@router.post("/{adapter_name}/mode", dependencies=[Depends(require_workspace_admin)])
def update_adapter_mode(adapter_name: str, payload: ModeUpdateRequest):
    """
    Switches an adapter's operational mode (MOCK, SANDBOX, PRODUCTION).
    Enforces server-side credentials and safety policies.
    """
    try:
        updated = adapter_registry.set_mode(adapter_name, payload.mode)
        return updated
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{adapter_name}/simulate-failure", dependencies=[Depends(require_workspace_admin)])
def simulate_adapter_failure(adapter_name: str, payload: SimulateFailureRequest):
    """
    Injects a resilience test failure scenario for non-production environments.
    """
    try:
        updated = adapter_registry.simulate_failure(adapter_name, payload.scenario)
        return updated
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{adapter_name}/test-connection")
def test_adapter_connection(adapter_name: str):
    """
    Performs a non-transactional connection handshake to verify endpoint availability.
    """
    try:
        result = adapter_registry.test_connection(adapter_name)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
