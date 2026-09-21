from datetime import datetime, timezone

from app.persistence.models import AuditEvent, SourceRecord
from app.persistence.repositories import AuditRepository, SourceRepository


def test_source_repository_deduplicates_and_preserves_retention_history(db_session):
    repository = SourceRepository(db_session)
    values = dict(source_type="manual_note", source_system_scope="manual", stable_external_id="n-1", manual_entry=True, provenance="test")
    first = repository.get_or_create_source(**values)
    assert repository.get_or_create_source(**values) is first
    db_session.flush()
    repository.mark_retention(first, "redacted", datetime.now(timezone.utc))
    assert first.retention_state == "redacted"


def test_idempotency_and_append_only_audit(db_session):
    source = SourceRecord(source_type="manual_note", source_system_scope="manual", manual_entry=True, provenance="test")
    db_session.add(source); db_session.flush()
    sources = SourceRepository(db_session)
    first = sources.reserve_idempotency(operation_kind="source", scope="manual", identity_key="one")
    assert sources.reserve_idempotency(operation_kind="source", scope="manual", identity_key="one") is first
    audit = AuditRepository(db_session)
    event = audit.append(event_type="source_created", affected_record_type="source_record", affected_record_id=source.id, actor_or_source="test", provenance="test")
    db_session.flush()
    assert audit.list_for("source_record", source.id) == [event]
    assert not hasattr(audit, "delete") and not hasattr(audit, "update")
