import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import EvidenceItem, Case
from backend.app.core.config import settings
from backend.app.services.audit_service import AuditService

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".docx", ".csv"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

class EvidenceService:
    @staticmethod
    def save_evidence(
        db: Session,
        tenant_id: str,
        case_id: str,
        file_name: str,
        file_content: bytes,
        uploaded_by_id: str,
        uploaded_by_name: str
    ) -> EvidenceItem:
        # Validate file size
        file_size = len(file_content)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum limit of 50MB ({file_size} bytes)")

        # Validate extension
        _, ext = os.path.splitext(file_name)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' is not supported. Allowed: {ALLOWED_EXTENSIONS}")

        # Compute SHA-256 checksum
        sha256_checksum = hashlib.sha256(file_content).hexdigest()

        # Create tenant and case scoped storage path
        tenant_storage = os.path.join(settings.STORAGE_DIR, tenant_id, case_id)
        os.makedirs(tenant_storage, exist_ok=True)
        safe_file_name = f"{sha256_checksum[:12]}_{os.path.basename(file_name)}"
        file_path = os.path.join(tenant_storage, safe_file_name)

        # Write file securely
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Infer file type
        file_type = "Document"
        if ext.lower() in [".png", ".jpg", ".jpeg"]:
            file_type = "Image"
        elif ext.lower() in [".xlsx", ".csv"]:
            file_type = "Spreadsheet"

        evidence = EvidenceItem(
            tenant_id=tenant_id,
            case_id=case_id,
            file_name=file_name,
            file_type=file_type,
            file_size_bytes=file_size,
            storage_path=file_path,
            sha256_checksum=sha256_checksum,
            validation_status="VALIDATED",
            uploaded_by_id=uploaded_by_id,
            uploaded_by_name=uploaded_by_name,
            created_at=datetime.now(timezone.utc)
        )
        db.add(evidence)
        db.flush()

        AuditService.record_event(
            db=db,
            tenant_id=tenant_id,
            action="evidence.uploaded",
            entity_type="evidence",
            entity_id=evidence.id,
            actor_id=uploaded_by_id,
            actor_name=uploaded_by_name,
            metadata={"file_name": file_name, "checksum": sha256_checksum, "size": file_size, "case_id": case_id}
        )
        db.commit()
        db.refresh(evidence)
        return evidence
