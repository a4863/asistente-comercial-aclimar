"""Account-wide thread reconstruction inside a caller-owned transaction."""

from dataclasses import dataclass
import sqlite3
import time
from typing import Literal

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.domain.email_threading import (
    EmailThreadInput,
    calculate_source_revision,
    reconstruct_threads,
)
from app.persistence.models import (
    Conversation,
    ConversationMembership,
    ThreadLineageEdge,
    ThreadMembershipChange,
)
from app.persistence.repositories import ThreadPersistenceRepository


_ERROR_CODES = frozenset({
    "invalid_scope", "invalid_source_state", "legacy_unresolved",
    "superseded_membership", "invalid_partition", "persistence_conflict",
})
_ACCEPTED = frozenset({"accepted_direct_parent", "accepted_ancestor"})


class ThreadReconstructionError(Exception):
    def __init__(self, code: str):
        if code not in _ERROR_CODES:
            raise ValueError("unknown reconstruction error code")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ThreadReconstructionCoreResult:
    account_scope: str
    reconstruction_key: str
    source_count: int
    component_count: int
    conversations_created: int
    memberships_changed: int
    lineage_operations_created: int


@dataclass(frozen=True, slots=True)
class ThreadReconstructionResult:
    account_scope: str
    status: Literal["completed", "busy_retry_later"]
    reconstruction_key: str | None
    source_count: int | None
    component_count: int | None
    conversations_created: int
    memberships_changed: int
    lineage_operations_created: int


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _acquisition_busy(exc: BaseException) -> bool:
    original = exc.orig if isinstance(exc, OperationalError) else exc
    if not isinstance(original, sqlite3.OperationalError):
        return False
    code = getattr(original, "sqlite_errorcode", None)
    if code is not None:
        return code & 0xFF in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
    return str(original).lower() in {"database is locked", "database is busy", "database table is locked"}


def reconstruct_account_threads(engine: Engine, account_scope: str) -> ThreadReconstructionResult:
    """Run one atomic account reconstruction with a reserved SQLite writer slot."""
    if not isinstance(account_scope, str) or not 1 <= len(account_scope) <= 100 or not account_scope.strip():
        raise ThreadReconstructionError("invalid_scope")

    for attempt in range(3):
        busy = False
        try:
            with engine.connect() as connection:
                if connection.dialect.name != "sqlite":
                    raise ThreadReconstructionError("persistence_conflict")
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                    raise ThreadReconstructionError("persistence_conflict")
                connection.exec_driver_sql("PRAGMA busy_timeout=0")
                # PRAGMAs create a SQLAlchemy logical transaction, but no SQLite
                # write reservation. End it before issuing the explicit BEGIN.
                connection.rollback()
                try:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                except (OperationalError, sqlite3.OperationalError) as exc:
                    connection.rollback()
                    if not _acquisition_busy(exc):
                        raise ThreadReconstructionError("persistence_conflict") from None
                    busy = True
                if not busy:
                    session = Session(bind=connection, join_transaction_mode="rollback_only")
                    try:
                        # Join the reserved connection without issuing another BEGIN.
                        session.connection()
                        core = reconstruct_account_threads_in_session(session, account_scope)
                        session.flush()
                        connection.commit()
                    except ThreadReconstructionError:
                        connection.rollback()
                        raise
                    except Exception:
                        connection.rollback()
                        raise ThreadReconstructionError("persistence_conflict") from None
                    finally:
                        session.close()
                    return ThreadReconstructionResult(account_scope, "completed",
                        core.reconstruction_key, core.source_count, core.component_count,
                        core.conversations_created, core.memberships_changed,
                        core.lineage_operations_created)
        except ThreadReconstructionError:
            raise
        except Exception:
            raise ThreadReconstructionError("persistence_conflict") from None
        if not busy:
            raise ThreadReconstructionError("persistence_conflict")
        if attempt < 2:
            _sleep(0.1)

    return ThreadReconstructionResult(account_scope, "busy_retry_later",
        None, None, None, 0, 0, 0)


def _snapshot_error(exc: ValueError) -> str:
    message = str(exc)
    if "scope" in message and "source" not in message:
        return "invalid_scope"
    if "retention state" in message or "missing EmailMessage" in message:
        return "invalid_source_state"
    return "invalid_partition"


def _validate_threading(result, source_ids: set[int]) -> tuple[dict[int, tuple[int, ...]], dict[int, int]]:
    if len(result.decisions) != len(result.evidence):
        raise ThreadReconstructionError("invalid_partition")
    components = {}
    seen = set()
    for component_index, component in enumerate(result.components):
        if not component or len(component) != len(set(component)) or tuple(sorted(component)) != component:
            raise ThreadReconstructionError("invalid_partition")
        for source_id in component:
            if source_id in seen:
                raise ThreadReconstructionError("invalid_partition")
            seen.add(source_id)
            components[source_id] = component_index
    if seen != source_ids:
        raise ThreadReconstructionError("invalid_partition")
    accepted = {}
    accepted_indices = set()
    for index, (evidence, decision) in enumerate(zip(result.evidence, result.decisions)):
        if (decision.evidence_index != index or evidence.source_record_id not in source_ids
                or evidence.account_scope != result.account_scope):
            raise ThreadReconstructionError("invalid_partition")
        if decision.outcome in _ACCEPTED:
            if (decision.target_source_record_id not in source_ids
                    or evidence.source_record_id in accepted):
                raise ThreadReconstructionError("invalid_partition")
            accepted[evidence.source_record_id] = index
            accepted_indices.add(index)
        elif decision.target_source_record_id is not None:
            raise ThreadReconstructionError("invalid_partition")
    edge_indices = set()
    for edge in result.edges:
        index = edge.evidence_index
        if (index not in accepted_indices or index in edge_indices
                or edge.source_record_id != result.evidence[index].source_record_id
                or edge.target_source_record_id != result.decisions[index].target_source_record_id
                or components[edge.source_record_id] != components[edge.target_source_record_id]):
            raise ThreadReconstructionError("invalid_partition")
        edge_indices.add(index)
    if edge_indices != accepted_indices:
        raise ThreadReconstructionError("invalid_partition")
    return ({index: component for index, component in enumerate(result.components)}, accepted)


def _groups(components, rows):
    old_to_new = {}
    new_to_old = {index: set() for index in components}
    source_to_new = {source_id: index for index, component in components.items()
                     for source_id in component}
    for row in rows:
        if row.current_conversation_id is not None:
            old_id = row.current_conversation_id
            new_index = source_to_new[row.source_record_id]
            old_to_new.setdefault(old_id, set()).add(new_index)
            new_to_old[new_index].add(old_id)
    groups = []
    visited = set()
    for start in sorted(components, key=lambda index: components[index][0]):
        if start in visited:
            continue
        pending = [start]
        new_indices = set()
        old_ids = set()
        while pending:
            index = pending.pop()
            if index in new_indices:
                continue
            new_indices.add(index)
            for old_id in new_to_old[index]:
                if old_id not in old_ids:
                    old_ids.add(old_id)
                    pending.extend(old_to_new[old_id])
        visited.update(new_indices)
        groups.append((tuple(sorted(old_ids)),
                       tuple(sorted(new_indices, key=lambda index: components[index][0]))))
    return tuple(groups)


def _classification(old_ids, new_indices, components, old_members):
    if not old_ids and len(new_indices) == 1:
        return "initial"
    if len(old_ids) == 1 and len(new_indices) == 1:
        return ("unchanged" if old_members[old_ids[0]] == set(components[new_indices[0]])
                else "correction")
    if len(old_ids) >= 2 and len(new_indices) == 1:
        return "merge"
    if len(old_ids) == 1 and len(new_indices) >= 2:
        return "split"
    if len(old_ids) >= 2 and len(new_indices) >= 2:
        return "repartition"
    raise ThreadReconstructionError("invalid_partition")


def reconstruct_account_threads_in_session(
    session: Session, account_scope: str,
) -> ThreadReconstructionCoreResult:
    """Reconstruct without owning transaction acquisition or completion."""
    if not isinstance(account_scope, str) or not 1 <= len(account_scope) <= 100 or not account_scope.strip():
        raise ThreadReconstructionError("invalid_scope")
    if not session.in_transaction():
        raise ThreadReconstructionError("persistence_conflict")
    try:
        repo = ThreadPersistenceRepository(session)
        snapshot = repo.load_account_thread_snapshot(account_scope)
    except ValueError as exc:
        raise ThreadReconstructionError(_snapshot_error(exc)) from None
    except Exception:
        raise ThreadReconstructionError("persistence_conflict") from None

    rows = tuple(row for row in snapshot.sources if row.eligible)
    source_ids = {row.source_record_id for row in rows}
    old_members = {}
    for row in rows:
        if row.current_conversation_id is None:
            continue
        if row.conversation_legacy_status == "legacy_unresolved":
            raise ThreadReconstructionError("legacy_unresolved")
        if row.conversation_superseded_at is not None:
            raise ThreadReconstructionError("superseded_membership")
        if row.conversation_legacy_status != "resolved" or row.conversation_account_scope != account_scope:
            raise ThreadReconstructionError("invalid_partition")
        for member in row.full_current_members:
            if member.source_type != "email_message" or member.account_scope != account_scope:
                raise ThreadReconstructionError("invalid_partition")
        members = set(row.full_current_member_ids)
        if len(members) != len(row.full_current_member_ids) or row.source_record_id not in members:
            raise ThreadReconstructionError("invalid_partition")
        prior = old_members.setdefault(row.current_conversation_id, members)
        if prior != members:
            raise ThreadReconstructionError("invalid_partition")

    try:
        inputs = []
        for row in rows:
            message = EmailThreadInput(account_scope, row.source_record_id,
                row.normalized_message_id, row.in_reply_to, row.references_header,
                row.subject, "")
            inputs.append(EmailThreadInput(account_scope, row.source_record_id,
                row.normalized_message_id, row.in_reply_to, row.references_header,
                row.subject, calculate_source_revision(message)))
        threading = reconstruct_threads(account_scope, tuple(inputs))
        if threading.account_scope != account_scope:
            raise ThreadReconstructionError("invalid_partition")
        components, accepted = _validate_threading(threading, source_ids)
        groups = _groups(components, rows)
        classifications = tuple((old_ids, new_indices,
            _classification(old_ids, new_indices, components, old_members))
            for old_ids, new_indices in groups)
    except ValueError:
        raise ThreadReconstructionError("invalid_partition") from None

    # Only after all corpus/topology checks do persistence primitives run.
    try:
        evidence_ids = []
        for item in threading.evidence:
            evidence = repo.append_evidence(account_scope=item.account_scope,
                source_record_id=item.source_record_id, header_kind=item.header_kind,
                ordinal=item.ordinal, parse_status=item.parse_status,
                canonical_token=item.canonical_token, token_digest=item.token_digest,
                normalization_version=item.normalization_version,
                source_revision=item.source_revision)
            evidence_ids.append(evidence.id)
        decision_ids = {}
        for item in threading.decisions:
            decision = repo.append_decision(evidence_id=evidence_ids[item.evidence_index],
                reconstruction_key=threading.reconstruction_key, outcome=item.outcome,
                target_source_record_id=item.target_source_record_id)
            decision_ids[item.evidence_index] = decision.id

        row_by_id = {row.source_record_id: row for row in rows}
        created = changed = lineage_count = 0
        expected = {}
        changed_source_ids = set()
        changed_old_ids = set()
        for old_ids, new_indices, kind in classifications:
            if kind == "unchanged":
                component = components[new_indices[0]]
                expected[frozenset(component)] = old_ids[0]
                continue
            successors = {}
            for index in new_indices:
                conversation = repo.create_resolved_conversation(account_scope, "thread_reconstruction")
                successors[index] = conversation.id
                expected[frozenset(components[index])] = conversation.id
                created += 1
            if old_ids:
                repo.record_lineage_operation(account_scope=account_scope, kind=kind,
                    predecessor_ids=sorted(old_ids), successor_ids=sorted(successors.values()),
                    reconstruction_key=threading.reconstruction_key)
                lineage_count += 1
                changed_old_ids.update(old_ids)
            for index in new_indices:
                component = components[index]
                for source_id in component:
                    old_id = row_by_id[source_id].current_conversation_id
                    edge_index = accepted.get(source_id)
                    decision_id = decision_ids[edge_index] if edge_index is not None else None
                    evidence_type = ("thread_decision" if decision_id is not None or len(component) > 1
                                     else "singleton")
                    evidence_reference = (f"decision:{decision_id}" if decision_id is not None
                                          else f"source:{source_id}")
                    repo.assign_current_membership(account_scope=account_scope,
                        source_record_id=source_id, new_conversation_id=successors[index],
                        reason=kind if old_id is not None else "initial_assignment",
                        reconstruction_key=threading.reconstruction_key,
                        evidence_type=evidence_type, evidence_reference=evidence_reference,
                        expected_old_conversation_id=old_id,
                        evidence_decision_id=decision_id)
                    changed_source_ids.add(source_id)
                    changed += 1

        # The caller still owns rollback if a postcondition fails.
        session.flush()
        memberships = session.scalars(select(ConversationMembership).where(
            ConversationMembership.source_record_id.in_(source_ids)
        )).all() if source_ids else ()
        if len(memberships) != len(source_ids):
            raise ThreadReconstructionError("invalid_partition")
        by_conversation = {}
        for membership in memberships:
            conversation = session.get(Conversation, membership.conversation_id)
            if (conversation is None or conversation.legacy_status != "resolved"
                    or conversation.account_scope != account_scope or conversation.superseded_at is not None):
                raise ThreadReconstructionError("invalid_partition")
            by_conversation.setdefault(conversation.id, set()).add(membership.source_record_id)
        if {frozenset(ids): conversation_id for conversation_id, ids in by_conversation.items()} != expected:
            raise ThreadReconstructionError("invalid_partition")
        histories = session.scalars(select(ThreadMembershipChange).where(
            ThreadMembershipChange.source_record_id.in_(changed_source_ids),
            ThreadMembershipChange.reconstruction_key == threading.reconstruction_key,
        )).all() if changed_source_ids else ()
        if {row.source_record_id for row in histories} != changed_source_ids:
            raise ThreadReconstructionError("invalid_partition")
        for old_id in changed_old_ids:
            if not repo.lineage_from(old_id):
                raise ThreadReconstructionError("invalid_partition")
        return ThreadReconstructionCoreResult(account_scope, threading.reconstruction_key,
            len(rows), len(components), created, changed, lineage_count)
    except ThreadReconstructionError:
        raise
    except Exception:
        raise ThreadReconstructionError("persistence_conflict") from None
