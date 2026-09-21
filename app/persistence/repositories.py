from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import AuditEvent, IdempotencyIdentity, SourceObservation, SourceRecord


class SourceRepository:
    def __init__(self, session: Session): self.session = session
    def get_or_create_source(self, **values):
        external_id = values.get("stable_external_id")
        if external_id:
            existing = self.session.scalar(select(SourceRecord).where(SourceRecord.source_system_scope == values["source_system_scope"], SourceRecord.stable_external_id == external_id))
            if existing: return existing
        record = SourceRecord(**values); self.session.add(record); return record
    def append_observation(self, **values):
        record = SourceObservation(**values); self.session.add(record); return record
    def reserve_idempotency(self, **values):
        existing = self.session.scalar(select(IdempotencyIdentity).where(IdempotencyIdentity.operation_kind == values["operation_kind"], IdempotencyIdentity.scope == values["scope"], IdempotencyIdentity.identity_key == values["identity_key"]))
        if existing: return existing
        record = IdempotencyIdentity(**values); self.session.add(record); return record
    def mark_retention(self, record: SourceRecord, state: str, at: datetime):
        record.retention_state, record.deleted_or_redacted_at = state, at


class AuditRepository:
    def __init__(self, session: Session): self.session = session
    def append(self, **values):
        forbidden = {"payload", "secret", "token", "password"} & values.keys()
        if forbidden: raise ValueError("unsafe audit fields")
        event = AuditEvent(**values); self.session.add(event); return event
    def list_for(self, record_type: str, record_id: int):
        return list(self.session.scalars(select(AuditEvent).where(AuditEvent.affected_record_type == record_type, AuditEvent.affected_record_id == record_id)))
