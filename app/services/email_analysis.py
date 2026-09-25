"""Local Phase 4 analysis orchestration; no concrete AI provider or external actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.domain.email_analysis import (
    AnalysisCandidates, AnalysisDomainError, AnalysisInput, NoAnalyzableBody,
    select_analysis_input,
)
from app.persistence.models import AnalysisRun, ConversationMembership, EmailMessage
from app.persistence.repositories import (
    AnalysisRepository, AnalysisRepositoryError, AnalysisSourceSnapshot,
)


class AIService(Protocol):
    def analyze(self, analysis_input: AnalysisInput) -> AnalysisCandidates: ...


class FakeAIServiceError(RuntimeError):
    """A bounded, deterministic fake-provider failure."""


class FakeAIService:
    """Test-only fake keyed by canonical digest; records no source content."""

    def __init__(self, outputs: dict[str, AnalysisCandidates] | None = None, *,
                 default_output: AnalysisCandidates | None = None, fail: bool = False):
        self._outputs = dict(outputs or {})
        self._default = default_output if default_output is not None else AnalysisCandidates()
        self.fail = fail
        self.calls: list[tuple[str, int, int]] = []

    def analyze(self, analysis_input: AnalysisInput) -> AnalysisCandidates:
        if not isinstance(analysis_input, AnalysisInput):
            raise FakeAIServiceError("invalid_input")
        self.calls.append((analysis_input.input_digest, analysis_input.contract_version,
                           analysis_input.policy_version))
        if self.fail:
            raise FakeAIServiceError("provider_failure")
        return self._outputs.get(analysis_input.input_digest, self._default)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    status: str
    run_id: int | None = None
    input_digest: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class ManualAnalysisOption:
    source_record_id: int
    sender: str
    subject: str
    message_date: str
    state: str


class AnalysisServiceError(ValueError):
    """Safe pre-reservation failure with no raw source or SQL text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _safe_label(value: str | None, limit: int, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return "".join(" " if ord(character) < 32 or ord(character) == 127 else character
                   for character in value)[:limit]


def list_manual_analysis_options(session_factory, account_scope: str, *,
                                 limit: int = 20) -> tuple[ManualAnalysisOption, ...]:
    """Read a bounded local selector; never return bodies or canonical digests."""
    try:
        with session_factory() as session, session.begin():
            repository = AnalysisRepository(session)
            refs = repository.list_eligible_email_refs(account_scope, limit=limit)
            options = []
            for ref in refs:
                try:
                    current = select_analysis_input(session, account_scope, ref.source_record_id)
                except (AnalysisDomainError, NoAnalyzableBody):
                    continue
                digest = current.input_digest
                latest = repository.latest_run_for_target(account_scope, ref.source_record_id)
                matching = (latest is not None and
                            (latest.input_digest, latest.contract_version, latest.policy_version)
                            == (digest, current.contract_version, current.policy_version))
                if matching and latest.status == "reserved":
                    state = "in_progress"
                elif repository.replay_lookup(account_scope, ref.source_record_id, digest,
                                              current.contract_version, current.policy_version):
                    state = "completed"
                elif matching and latest.status in {"failed_retryable", "stale_retryable"}:
                    state = "retry_required"
                else:
                    state = "ready"
                date = ref.message_date
                date_label = date.isoformat()[:35] if isinstance(date, datetime) else "unknown"
                options.append(ManualAnalysisOption(
                    ref.source_record_id, _safe_label(ref.sender, 120, "Unknown sender"),
                    _safe_label(ref.subject, 160, "No subject"), date_label, state))
            return tuple(options)
    except (SQLAlchemyError, AnalysisRepositoryError) as error:
        raise AnalysisServiceError("persistence_failure") from None


def _conversation_id(session, source_record_id: int) -> int:
    conversation_id = session.scalar(select(ConversationMembership.conversation_id).where(
        ConversationMembership.source_record_id == source_record_id))
    if conversation_id is None:
        raise AnalysisServiceError("invalid_target")
    return conversation_id


def _snapshot(session, analysis_input: AnalysisInput) -> AnalysisSourceSnapshot:
    selected_ids = tuple(item.source_record_id for item in analysis_input.selected_messages)
    rows = dict(session.execute(
        select(EmailMessage.source_record_id, EmailMessage.normalized_body)
        .where(EmailMessage.source_record_id.in_(selected_ids))
    ).all())
    if set(rows) != set(selected_ids) or not isinstance(rows[selected_ids[0]], str):
        raise AnalysisServiceError("invalid_source_snapshot")
    return AnalysisSourceSnapshot(analysis_input, tuple((source_id, rows[source_id])
                                                       for source_id in selected_ids))


def _mark_retryable(session_factory, run_id: int, input_digest: str, *,
                    status: str, failure_code: str) -> AnalysisResult:
    """After rollback, query the durable run before writing a bounded failure."""
    try:
        with session_factory() as session:
            with session.begin():
                run = session.get(AnalysisRun, run_id)
                if run is None:
                    return AnalysisResult("in_progress", run_id, input_digest,
                                          "persistence_failure")
                if run.status == "completed":
                    return AnalysisResult("completed", run_id, input_digest)
                if run.status != "reserved":
                    return AnalysisResult(run.status, run_id, input_digest,
                                          run.failure_code)
                AnalysisRepository(session).mark_retryable(
                    run_id, status=status, failure_code=failure_code)
        return AnalysisResult(status, run_id, input_digest, failure_code)
    except (AnalysisRepositoryError, SQLAlchemyError):
        # The reservation may still be live; never claim a persisted failure.
        return AnalysisResult("in_progress", run_id, input_digest,
                              "persistence_failure")


def _manual_conflict_result(session_factory, account_scope: str, target_source_record_id: int,
                            input_digest: str, contract_version: int,
                            policy_version: int) -> AnalysisResult:
    try:
        with session_factory() as session:
            latest = AnalysisRepository(session).latest_run_for_target(
                account_scope, target_source_record_id)
            if (latest is not None and latest.status == "reserved" and
                    (latest.input_digest, latest.contract_version, latest.policy_version) ==
                    (input_digest, contract_version, policy_version)):
                return AnalysisResult("in_progress", latest.id, input_digest)
    except SQLAlchemyError:
        pass
    return AnalysisResult("unavailable")


def analyze_email_in_thread(session_factory, ai_service: AIService,
                            account_scope: str, target_source_record_id: int, *,
                            request_mode: str = "automatic", contract_version: int = 1,
                            policy_version: int = 1,
                            force_reanalysis: bool = False,
                            manual_intent: str | None = None) -> AnalysisResult:
    """Reserve, call AI outside any session, then revalidate and append atomically."""
    mode = "force" if force_reanalysis else request_mode
    if mode not in {"automatic", "manual", "force"}:
        raise AnalysisServiceError("invalid_request_mode")
    if manual_intent is not None and (mode != "manual" or
                                      manual_intent not in {"initial", "retry"}):
        raise AnalysisServiceError("invalid_request_mode")
    try:
        with session_factory() as session:
            with session.begin():
                analysis_input = select_analysis_input(
                    session, account_scope, target_source_record_id,
                    contract_version=contract_version, policy_version=policy_version)
                snapshot = _snapshot(session, analysis_input)
                conversation_id = _conversation_id(session, target_source_record_id)
                repository = AnalysisRepository(session)
                if manual_intent is None:
                    reservation = repository.reserve_run(
                        account_scope, target_source_record_id, conversation_id,
                        analysis_input.input_digest, contract_version, policy_version, mode)
                else:
                    reservation = repository.reserve_manual_run(
                        account_scope, target_source_record_id, conversation_id,
                        analysis_input.input_digest, contract_version, policy_version,
                        intent=manual_intent)
                run_id = reservation.run.id if reservation.run is not None else None
                run_conversation_id = (reservation.run.conversation_id
                                       if reservation.run is not None else None)
                outcome = reservation.outcome
    except NoAnalyzableBody:
        return AnalysisResult("no_analyzable_body")
    except AnalysisRepositoryError as error:
        if error.code == "reservation_conflict" and manual_intent is not None:
            return _manual_conflict_result(session_factory, account_scope,
                                           target_source_record_id, analysis_input.input_digest,
                                           contract_version, policy_version)
        raise AnalysisServiceError("invalid_target" if error.code == "invalid_target"
                                   else "invalid_analysis_request") from None
    except (AnalysisDomainError, AnalysisServiceError) as error:
        raise AnalysisServiceError("invalid_target" if getattr(error, "code", "") in {
            "invalid_target", "invalid_conversation"} else "invalid_analysis_request") from None
    except SQLAlchemyError:
        raise AnalysisServiceError("persistence_failure") from None

    if outcome == "completed_replay":
        return AnalysisResult("completed_replay", run_id, analysis_input.input_digest)
    if outcome == "in_progress":
        return AnalysisResult("in_progress", run_id, analysis_input.input_digest)
    if outcome in {"retry_required", "retry_not_available"}:
        return AnalysisResult(outcome, run_id, analysis_input.input_digest)

    assert run_id is not None and run_conversation_id is not None

    # The reservation transaction has committed and its Session is closed here.
    try:
        candidates = ai_service.analyze(analysis_input)
    except Exception:
        return _mark_retryable(session_factory, run_id, analysis_input.input_digest,
                               status="failed_retryable", failure_code="provider_failure")
    if not isinstance(candidates, AnalysisCandidates):
        return _mark_retryable(session_factory, run_id, analysis_input.input_digest,
                               status="failed_retryable", failure_code="invalid_output")
    try:
        AnalysisCandidates(**{name: getattr(candidates, name)
                              for name in AnalysisCandidates.__dataclass_fields__})
    except (AnalysisDomainError, AttributeError, TypeError, ValueError):
        return _mark_retryable(session_factory, run_id, analysis_input.input_digest,
                               status="failed_retryable", failure_code="invalid_output")

    try:
        with session_factory() as session:
            with session.begin():
                try:
                    current = select_analysis_input(
                        session, account_scope, target_source_record_id,
                        contract_version=contract_version, policy_version=policy_version)
                    current_conversation_id = _conversation_id(session, target_source_record_id)
                except (AnalysisDomainError, AnalysisServiceError):
                    current = None
                    current_conversation_id = None
                repository = AnalysisRepository(session)
                if current != analysis_input or current_conversation_id != run_conversation_id:
                    repository.mark_retryable(run_id, status="stale_retryable",
                                              failure_code="input_changed")
                    return AnalysisResult("stale_retryable", run_id,
                                          analysis_input.input_digest, "input_changed")
                repository.complete_run(run_id, analysis_input.input_digest,
                                        candidates, snapshot)
        return AnalysisResult("completed", run_id, analysis_input.input_digest)
    except AnalysisRepositoryError as error:
        if error.code in {"input_changed", "invalid_target"}:
            status, code = "stale_retryable", "input_changed"
        elif error.code in {"invalid_output", "invalid_evidence", "invalid_quote_state",
                            "invalid_summary"}:
            status, code = "failed_retryable", "invalid_output"
        else:
            status, code = "failed_retryable", "persistence_failure"
        return _mark_retryable(session_factory, run_id, analysis_input.input_digest,
                               status=status, failure_code=code)
    except Exception:
        return _mark_retryable(session_factory, run_id, analysis_input.input_digest,
                               status="failed_retryable", failure_code="persistence_failure")
