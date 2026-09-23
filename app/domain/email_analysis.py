"""Bounded, read-only canonical input for Phase 4 email analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Literal

from sqlalchemy import select

from app.persistence.models import Conversation, ConversationMembership, EmailMessage, SourceRecord


_PREFIX = b"phase4/analysis-input/v1\0"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_MAIL_QUOTE = re.compile(r"On .+ wrote:\s*\Z", re.IGNORECASE)
_ORIGINAL_MESSAGE = re.compile(r"-{2,}\s*Original Message\s*-{2,}\s*\Z", re.IGNORECASE)
_UNCERTAIN_HEADER = re.compile(r"(?:From|De|Sent|Enviado|To|Para|Subject|Asunto):\s*.+", re.IGNORECASE)


class AnalysisDomainError(ValueError):
    """Bounded validation failure; never includes source or candidate text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class NoAnalyzableBody(AnalysisDomainError):
    def __init__(self):
        super().__init__("no_analyzable_body")


def _require(condition: bool, code: str = "invalid_candidate") -> None:
    if not condition:
        raise AnalysisDomainError(code)


def _text(value: object, *, maximum: int | None = None) -> None:
    _require(isinstance(value, str) and bool(value) and (maximum is None or len(value) <= maximum))


def _enum(value: object, choices: frozenset[str]) -> None:
    _require(isinstance(value, str) and value in choices)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _date(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    # Existing IMAP persistence stores UTC as naive SQLite datetime.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _date_text(value: datetime | None) -> str | None:
    normalized = _date(value)
    return normalized.isoformat() if normalized is not None else None


@dataclass(frozen=True, slots=True)
class SelectedMessage:
    source_record_id: int
    role: Literal["target", "prior"]
    body_excerpt: str
    original_body_digest: str
    sender: str | None
    recipients: tuple[str, ...]
    subject: str | None
    message_date: datetime | None

    def __post_init__(self):
        _require(type(self.source_record_id) is int and self.source_record_id > 0)
        _enum(self.role, frozenset({"target", "prior"}))
        _require(isinstance(self.body_excerpt, str))
        _require(isinstance(self.original_body_digest, str) and _HEX64.fullmatch(self.original_body_digest) is not None)
        _require(self.sender is None or isinstance(self.sender, str))
        _require(self.subject is None or isinstance(self.subject, str))
        _require(type(self.recipients) is tuple and all(isinstance(item, str) for item in self.recipients))
        _require(self.message_date is None or isinstance(self.message_date, datetime))


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    account_scope: str
    target_source_record_id: int
    contract_version: int
    policy_version: int
    selected_messages: tuple[SelectedMessage, ...]
    input_digest: str

    def __post_init__(self):
        _text(self.account_scope, maximum=100)
        _require(type(self.target_source_record_id) is int and self.target_source_record_id > 0)
        _require(type(self.contract_version) is int and self.contract_version > 0)
        _require(type(self.policy_version) is int and self.policy_version > 0)
        _require(type(self.selected_messages) is tuple and bool(self.selected_messages))
        _require(self.selected_messages[0].role == "target" and self.selected_messages[0].source_record_id == self.target_source_record_id)
        _require(all(message.role == "prior" for message in self.selected_messages[1:]))
        _require(len({message.source_record_id for message in self.selected_messages}) == len(self.selected_messages))
        _require(len(self.selected_messages) <= 7)
        _require(sum(len(message.body_excerpt) for message in self.selected_messages) <= 30000)
        _require(isinstance(self.input_digest, str) and _HEX64.fullmatch(self.input_digest) is not None)


def canonical_analysis_bytes(account_scope: str, target_source_record_id: int,
                             contract_version: int, policy_version: int,
                             selected_messages: tuple[SelectedMessage, ...]) -> bytes:
    """Stable, field-allowlisted serialization; no ORM state enters the digest."""
    payload = {
        "account_scope": account_scope,
        "target_source_record_id": target_source_record_id,
        "contract_version": contract_version,
        "policy_version": policy_version,
        "selected_messages": [
            {
                "source_record_id": item.source_record_id,
                "role": item.role,
                "body_excerpt": item.body_excerpt,
                "original_body_digest": item.original_body_digest,
                "sender": item.sender,
                "recipients": item.recipients,
                "subject": item.subject,
                "message_date": _date_text(item.message_date),
            }
            for item in selected_messages
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _recipients(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisDomainError("invalid_recipient_metadata") from None
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise AnalysisDomainError("invalid_recipient_metadata")
    return tuple(decoded)


def _eligible(source: SourceRecord, email: EmailMessage, account_scope: str) -> bool:
    return (
        source.source_type == "email_message"
        and source.source_system_scope == account_scope
        and source.retention_state == "active"
        and source.deleted_or_redacted_at is None
        and email.source_record_id == source.id
    )


def _message_date(email: EmailMessage) -> datetime | None:
    return _date(email.sent_at if email.sent_at is not None else email.received_at)


def select_analysis_input(session, account_scope: str, target_source_record_id: int, *,
                          contract_version: int = 1, policy_version: int = 1,
                          max_prior: int = 6, max_body_chars: int = 30000) -> AnalysisInput:
    """Read the current conversation without flushing, writing or owning the transaction."""
    _text(account_scope, maximum=100)
    _require(type(target_source_record_id) is int and target_source_record_id > 0, "invalid_target")
    _require(type(contract_version) is int and contract_version > 0, "invalid_version")
    _require(type(policy_version) is int and policy_version > 0, "invalid_version")
    _require(type(max_prior) is int and 0 <= max_prior <= 6, "invalid_limit")
    _require(type(max_body_chars) is int and 1 <= max_body_chars <= 30000, "invalid_limit")
    with session.no_autoflush:
        target = session.execute(
            select(SourceRecord, EmailMessage, Conversation)
            .join(EmailMessage, EmailMessage.source_record_id == SourceRecord.id)
            .join(ConversationMembership, ConversationMembership.source_record_id == SourceRecord.id)
            .join(Conversation, Conversation.id == ConversationMembership.conversation_id)
            .where(SourceRecord.id == target_source_record_id)
        ).one_or_none()
        if target is None:
            raise AnalysisDomainError("invalid_target")
        source, email, conversation = target
        if not _eligible(source, email, account_scope):
            raise AnalysisDomainError("invalid_target")
        if (conversation.legacy_status != "resolved" or conversation.superseded_at is not None
                or conversation.account_scope != account_scope):
            raise AnalysisDomainError("invalid_conversation")
        if email.normalized_body is None:
            raise NoAnalyzableBody()
        rows = session.execute(
            select(SourceRecord, EmailMessage)
            .join(EmailMessage, EmailMessage.source_record_id == SourceRecord.id)
            .join(ConversationMembership, ConversationMembership.source_record_id == SourceRecord.id)
            .where(ConversationMembership.conversation_id == conversation.id,
                   SourceRecord.id != target_source_record_id)
        ).all()

    target_date = _message_date(email)
    priors = []
    for prior_source, prior_email in rows:
        if not _eligible(prior_source, prior_email, account_scope):
            continue
        prior_date = _message_date(prior_email)
        if target_date is not None and prior_date is not None:
            is_prior = prior_date < target_date or (
                prior_date == target_date and prior_source.id < target_source_record_id
            )
        else:
            is_prior = prior_source.id < target_source_record_id
        if is_prior:
            priors.append((prior_source, prior_email, prior_date))
    priors.sort(key=lambda row: (row[2] is not None,
                                 row[2] or datetime.min.replace(tzinfo=timezone.utc),
                                 row[0].id), reverse=True)
    selected = [(source, email, target_date, "target")]
    selected.extend((prior_source, prior_email, prior_date, "prior")
                    for prior_source, prior_email, prior_date in priors[:max_prior])

    budget = max_body_chars
    messages = []
    for selected_source, selected_email, message_date, role in selected:
        original_body = selected_email.normalized_body or ""
        excerpt = original_body[:budget]
        budget -= len(excerpt)
        messages.append(SelectedMessage(
            source_record_id=selected_source.id, role=role,
            body_excerpt=excerpt, original_body_digest=_digest(original_body),
            sender=selected_email.sender_address,
            recipients=_recipients(selected_email.recipient_addresses),
            subject=selected_email.subject, message_date=message_date,
        ))
    selected_messages = tuple(messages)
    digest = sha256(_PREFIX + canonical_analysis_bytes(
        account_scope, target_source_record_id, contract_version, policy_version,
        selected_messages,
    )).hexdigest()
    return AnalysisInput(account_scope, target_source_record_id, contract_version,
                         policy_version, selected_messages, digest)


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    source_record_id: int
    start_offset: int
    end_offset: int
    span_digest: str
    exact_text: str

    def __post_init__(self):
        _require(type(self.source_record_id) is int and self.source_record_id > 0)
        _require(type(self.start_offset) is int and self.start_offset >= 0)
        _require(type(self.end_offset) is int and self.end_offset > self.start_offset)
        _require(isinstance(self.span_digest, str) and _HEX64.fullmatch(self.span_digest) is not None)
        _text(self.exact_text)


def validate_evidence(candidate: EvidenceCandidate, original_body: str,
                      selected_message: SelectedMessage) -> None:
    """Validate original-body evidence and that the provider saw the span."""
    _require(isinstance(original_body, str), "invalid_evidence")
    _require(candidate.source_record_id == selected_message.source_record_id, "invalid_evidence")
    _require(_digest(original_body) == selected_message.original_body_digest, "invalid_evidence")
    _require(candidate.end_offset <= len(original_body), "invalid_evidence")
    _require(candidate.end_offset <= len(selected_message.body_excerpt), "invalid_evidence")
    _require(original_body[candidate.start_offset:candidate.end_offset] == candidate.exact_text,
             "invalid_evidence")
    _require(_digest(candidate.exact_text) == candidate.span_digest, "invalid_evidence")
    _require(selected_message.body_excerpt[candidate.start_offset:candidate.end_offset]
             == candidate.exact_text, "invalid_evidence")


def classify_quote(original_body: str, candidate: EvidenceCandidate) -> Literal["new", "quoted", "ambiguous"]:
    """Conservative line-based quote signal, not a quote/signature remover."""
    _require(candidate.end_offset <= len(original_body), "invalid_evidence")
    lines = original_body.splitlines(keepends=True)
    start = 0
    current = 0
    for index, line in enumerate(lines):
        if start <= candidate.start_offset < start + len(line):
            current = index
            break
        start += len(line)
    current_line = lines[current] if lines else ""
    if current_line.startswith(">"):
        return "quoted"
    earlier = [line.strip() for line in lines[:current]]
    if any(_MAIL_QUOTE.fullmatch(line) or _ORIGINAL_MESSAGE.fullmatch(line) for line in earlier):
        return "quoted"
    if current_line.lstrip().startswith(">") or any(
        _UNCERTAIN_HEADER.fullmatch(line) for line in earlier
    ):
        return "ambiguous"
    return "new"


def current_question_eligible(analysis_input: AnalysisInput, candidate: EvidenceCandidate,
                              original_body: str) -> bool:
    if candidate.source_record_id != analysis_input.target_source_record_id:
        return False
    validate_evidence(candidate, original_body, analysis_input.selected_messages[0])
    return classify_quote(original_body, candidate) == "new"


def _support_indexes(indexes: tuple[int, ...]) -> None:
    _require(type(indexes) is tuple and all(type(index) is int and index >= 0 for index in indexes))


@dataclass(frozen=True, slots=True)
class FactCandidate:
    fact_type: str
    value_reference: str
    evidence: EvidenceCandidate

    def __post_init__(self):
        _text(self.fact_type, maximum=100)
        _text(self.value_reference, maximum=255)
        _require(isinstance(self.evidence, EvidenceCandidate))


@dataclass(frozen=True, slots=True)
class InferenceCandidate:
    inference_type: str
    value_reference: str
    support_indexes: tuple[int, ...]
    evidence: EvidenceCandidate | None = None

    def __post_init__(self):
        _text(self.inference_type, maximum=100)
        _text(self.value_reference, maximum=255)
        _support_indexes(self.support_indexes)
        _require(self.evidence is None or isinstance(self.evidence, EvidenceCandidate))


@dataclass(frozen=True, slots=True)
class ProposalCandidate:
    proposal_type: str
    value_reference: str
    support_indexes: tuple[int, ...]
    evidence: EvidenceCandidate | None = None

    def __post_init__(self):
        _text(self.proposal_type, maximum=100)
        _text(self.value_reference, maximum=255)
        _support_indexes(self.support_indexes)
        _require(self.evidence is None or isinstance(self.evidence, EvidenceCandidate))


@dataclass(frozen=True, slots=True)
class QuestionCandidate:
    question_text: str
    evidence: EvidenceCandidate
    quote_state: Literal["new", "quoted", "ambiguous"]

    def __post_init__(self):
        _text(self.question_text)
        _require(isinstance(self.evidence, EvidenceCandidate))
        _require(self.question_text == self.evidence.exact_text)
        _enum(self.quote_state, frozenset({"new", "quoted", "ambiguous"}))


@dataclass(frozen=True, slots=True)
class CommitmentCandidate:
    description: str
    responsible_party: Literal["self", "counterparty", "unknown"]
    date_certainty: Literal["exact", "resolved_relative", "uncertain", "none"]
    date_expression: str | None
    resolved_due_at: datetime | None
    evidence: EvidenceCandidate
    explicit_promise: bool

    def __post_init__(self):
        _text(self.description, maximum=255)
        _enum(self.responsible_party, frozenset({"self", "counterparty", "unknown"}))
        _enum(self.date_certainty, frozenset({"exact", "resolved_relative", "uncertain", "none"}))
        _require(self.date_expression is None or
                 (isinstance(self.date_expression, str) and 0 < len(self.date_expression) <= 255))
        _require(self.resolved_due_at is None or isinstance(self.resolved_due_at, datetime))
        _require(isinstance(self.evidence, EvidenceCandidate) and type(self.explicit_promise) is bool)
        if self.date_certainty in {"exact", "resolved_relative"}:
            _require(self.resolved_due_at is not None)
        else:
            _require(self.resolved_due_at is None)
        if self.date_certainty == "resolved_relative":
            _require(self.date_expression is not None)


@dataclass(frozen=True, slots=True)
class TaskCandidate:
    title: str
    due_at: datetime | None
    support_indexes: tuple[int, ...]

    def __post_init__(self):
        _text(self.title, maximum=255)
        _require(self.due_at is None or isinstance(self.due_at, datetime))
        _support_indexes(self.support_indexes)


@dataclass(frozen=True, slots=True)
class NextStepCandidate:
    description: str
    target_at: datetime | None
    support_indexes: tuple[int, ...]

    def __post_init__(self):
        _text(self.description, maximum=255)
        _require(self.target_at is None or isinstance(self.target_at, datetime))
        _support_indexes(self.support_indexes)


@dataclass(frozen=True, slots=True)
class ContextMention:
    kind: Literal["company", "contact", "work", "opportunity", "offer"]
    text: str
    evidence: EvidenceCandidate

    def __post_init__(self):
        _enum(self.kind, frozenset({"company", "contact", "work", "opportunity", "offer"}))
        _text(self.text)
        _require(isinstance(self.evidence, EvidenceCandidate))


@dataclass(frozen=True, slots=True)
class AnalysisCandidates:
    summary: str | None = None
    facts: tuple[FactCandidate, ...] = ()
    inferences: tuple[InferenceCandidate, ...] = ()
    proposals: tuple[ProposalCandidate, ...] = ()
    questions: tuple[QuestionCandidate, ...] = ()
    commitments: tuple[CommitmentCandidate, ...] = ()
    tasks: tuple[TaskCandidate, ...] = ()
    next_steps: tuple[NextStepCandidate, ...] = ()
    response_needed: Literal["yes", "no", "uncertain"] | None = None
    commercial_risk: Literal["none", "low", "medium", "high", "unknown"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    context_mentions: tuple[ContextMention, ...] = ()

    def __post_init__(self):
        if self.summary is not None:
            _text(self.summary, maximum=4000)
        for field, kind in (
            (self.facts, FactCandidate), (self.inferences, InferenceCandidate),
            (self.proposals, ProposalCandidate), (self.questions, QuestionCandidate),
            (self.commitments, CommitmentCandidate), (self.tasks, TaskCandidate),
            (self.next_steps, NextStepCandidate), (self.context_mentions, ContextMention),
        ):
            _require(type(field) is tuple and all(isinstance(item, kind) for item in field))
        if self.response_needed is not None:
            _enum(self.response_needed, frozenset({"yes", "no", "uncertain"}))
        if self.commercial_risk is not None:
            _enum(self.commercial_risk, frozenset({"none", "low", "medium", "high", "unknown"}))
        if self.priority is not None:
            _enum(self.priority, frozenset({"low", "normal", "high", "urgent"}))
