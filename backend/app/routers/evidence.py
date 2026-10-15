import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database.session import get_db
from backend.app.models.entities import EvidenceItem, Case
from backend.app.models.schemas import EvidenceResponse
from backend.app.services.evidence_service import EvidenceService
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/evidence", tags=["Evidence Ingestion"])

@router.get("/", response_model=List[EvidenceResponse])
def list_evidence(
    case_id: Optional[str] = None,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    query = db.query(EvidenceItem).filter(EvidenceItem.tenant_id == tenant.id)
    if case_id:
        query = query.filter(EvidenceItem.case_id == case_id)
    return query.order_by(EvidenceItem.created_at.desc()).all()

@router.post("/upload", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx

    # If no case_id specified, link to the most recent case or create an unattached request
    if not case_id:
        most_recent_case = db.query(Case).filter(Case.tenant_id == tenant.id).order_by(Case.created_at.desc()).first()
        if not most_recent_case:
            raise HTTPException(status_code=400, detail="No active cases available to attach evidence to")
        case_id = most_recent_case.id

    # Verify case exists and belongs to this tenant
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found in current workspace")

    content = await file.read()
    try:
        evidence = EvidenceService.save_evidence(
            db=db,
            tenant_id=tenant.id,
            case_id=case.id,
            file_name=file.filename or "evidence.pdf",
            file_content=content,
            uploaded_by_id=user.id,
            uploaded_by_name=user.full_name
        )
        return evidence
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: str,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    evidence = db.query(EvidenceItem).filter(
        EvidenceItem.id == evidence_id,
        EvidenceItem.tenant_id == tenant.id
    ).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    if not os.path.exists(evidence.storage_path):
        raise HTTPException(status_code=404, detail="File storage payload missing or archived")

    return FileResponse(
        path=evidence.storage_path,
        filename=evidence.file_name,
        media_type="application/octet-stream"
    )
