import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import AuditEvent

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

class AuditService:
    @staticmethod
    def record_event(
        db: Session,
        tenant_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
        actor_name: str = "Jordan Davies",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        metadata = metadata or {}
        now = datetime.now(timezone.utc)
        meta_str = json.dumps(metadata, sort_keys=True)
        
        # Fetch the most recent audit event for this tenant to get previous hash
        last_event = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id
        ).order_by(AuditEvent.created_at.desc()).first()
        
        prev_hash = last_event.current_hash if last_event else GENESIS_HASH
        
        # Calculate SHA-256 current hash
        raw_payload = f"{prev_hash}:{tenant_id}:{actor_id or 'anon'}:{action}:{entity_type}:{entity_id}:{now.isoformat()}:{meta_str}"
        current_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        
        audit_event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata_json=meta_str,
            prev_hash=prev_hash,
            current_hash=current_hash,
            created_at=now
        )
        
        db.add(audit_event)
        db.flush()
        return audit_event

    @staticmethod
    def verify_integrity(db: Session, tenant_id: str) -> Dict[str, Any]:
        """
        Verifies the cryptographic hash chain of the tenant's audit trail.
        """
        events = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id
        ).order_by(AuditEvent.created_at.asc()).all()
        
        prev_hash = GENESIS_HASH
        tampered_events = []
        
        for event in events:
            if event.prev_hash != prev_hash:
                tampered_events.append(event.id)
            prev_hash = event.current_hash
            
        return {
            "total_events": len(events),
            "is_valid": len(tampered_events) == 0,
            "tampered_count": len(tampered_events),
            "tampered_ids": tampered_events
        }
