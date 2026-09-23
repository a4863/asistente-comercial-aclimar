from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.domain.email_analysis import (
    AnalysisCandidates, AnalysisDomainError, AnalysisInput, CommitmentCandidate,
    ContextMention, EvidenceCandidate, FactCandidate, InferenceCandidate,
    NextStepCandidate, NoAnalyzableBody, ProposalCandidate, QuestionCandidate,
    SelectedMessage, TaskCandidate, canonical_analysis_bytes, classify_quote,
    current_question_eligible, select_analysis_input, validate_evidence,
)
from app.persistence.models import Conversation, ConversationMembership, EmailMessage, SourceRecord


DAY = datetime(2026, 1, 10, tzinfo=timezone.utc)


def _conversation(session, *, scope="imap:one", status="resolved", superseded=False):
    row = Conversation(account_scope=scope if status == "resolved" else None,
                       stable_key=str(uuid4()), legacy_status=status,
                       superseded_at=DAY if superseded else None, provenance="test")
    session.add(row)
    session.flush()
    return row


def _email(session, conversation, *, body="body", date=DAY, received=None,
           scope="imap:one", source_type="email_message", retention="active",
           redacted=False, sender="a@example.test", recipients=("b@example.test",),
           subject="Project"):
    source = SourceRecord(source_type=source_type, source_system_scope=scope,
                          stable_external_id=str(uuid4()), retention_state=retention,
                          deleted_or_redacted_at=DAY if redacted else None,
                          provenance="test")
    session.add(source)
    session.flush()
    email = EmailMessage(source_record_id=source.id, normalized_body=body,
                         sent_at=date, received_at=received, sender_address=sender,
                         recipient_addresses=json.dumps(recipients), subject=subject,
                         provenance="test")
    membership = ConversationMembership(conversation_id=conversation.id,
                                        source_record_id=source.id,
                                        evidence_type="test", evidence_reference="test")
    session.add_all((email, membership))
    session.flush()
    return source, email


def _selection(session, target, **kwargs):
    return select_analysis_input(session, "imap:one", target.id, **kwargs)


def _span(source_id, body, start, end):
    part = body[start:end]
    return EvidenceCandidate(source_id, start, end, sha256(part.encode()).hexdigest(), part)


def test_target_only_canonical_payload_and_allowlist(db_session):
    conversation = _conversation(db_session)
    target, email = _email(db_session, conversation, body="Café 🌍")
    result = _selection(db_session, target)
    assert len(result.selected_messages) == 1
    selected = result.selected_messages[0]
    assert selected.role == "target"
    assert selected.body_excerpt == "Café 🌍"
    assert selected.recipients == ("b@example.test",)
    payload = canonical_analysis_bytes(result.account_scope, result.target_source_record_id,
                                       result.contract_version, result.policy_version,
                                       result.selected_messages)
    assert b"Caf\xc3\xa9" in payload
    assert result.input_digest == sha256(b"phase4/analysis-input/v1\0" + payload).hexdigest()
    assert set(json.loads(payload)) == {"account_scope", "target_source_record_id",
                                        "contract_version", "policy_version", "selected_messages"}
    assert set(json.loads(payload)["selected_messages"][0]) == {
        "source_record_id", "role", "body_excerpt", "original_body_digest",
        "sender", "recipients", "subject", "message_date",
    }
    assert "conversation" not in payload.decode()
    assert "attachment" not in payload.decode()
    assert "stable_external_id" not in payload.decode()
    assert "location" not in payload.decode()
    assert email.source_record_id == target.id


def test_six_prior_limit_and_deterministic_newest_order(db_session):
    conversation = _conversation(db_session)
    prior = [_email(db_session, conversation, body=str(index), date=DAY - timedelta(days=10 - index))[0]
             for index in range(8)]
    target, _ = _email(db_session, conversation, body="target", date=DAY)
    selected = _selection(db_session, target).selected_messages
    assert [item.source_record_id for item in selected] == [target.id] + [item.id for item in reversed(prior[2:])]
    assert all(item.role == "prior" for item in selected[1:])
    assert _selection(db_session, target).selected_messages == selected


def test_timestamp_ties_and_missing_date_fallback(db_session):
    conversation = _conversation(db_session)
    same, _ = _email(db_session, conversation, date=DAY)
    dateless, _ = _email(db_session, conversation, date=None)
    received, _ = _email(db_session, conversation, date=None, received=DAY - timedelta(days=1))
    future, _ = _email(db_session, conversation, date=DAY + timedelta(days=1))
    target, _ = _email(db_session, conversation, date=DAY)
    selected = _selection(db_session, target).selected_messages
    assert [row.source_record_id for row in selected] == [target.id, same.id, received.id, dateless.id]
    assert future.id not in [row.source_record_id for row in selected]
    assert selected[-1].message_date is None
    later_target, _ = _email(db_session, conversation, date=None)
    selected_missing_target = _selection(db_session, later_target).selected_messages
    assert future.id in [row.source_record_id for row in selected_missing_target]


def test_excludes_redacted_deleted_different_scope_and_conversation(db_session):
    conversation = _conversation(db_session)
    active, _ = _email(db_session, conversation, body="active")
    redacted, _ = _email(db_session, conversation, redacted=True)
    deleted, _ = _email(db_session, conversation, retention="deleted_at_source")
    wrong_scope, _ = _email(db_session, conversation, scope="imap:two")
    other_conversation = _conversation(db_session)
    unrelated, _ = _email(db_session, other_conversation)
    target, _ = _email(db_session, conversation)
    ids = [message.source_record_id for message in _selection(db_session, target).selected_messages]
    assert ids == [target.id, active.id]
    assert not {redacted.id, deleted.id, wrong_scope.id, unrelated.id} & set(ids)


@pytest.mark.parametrize("status,superseded", [("legacy_unresolved", False), ("resolved", True)])
def test_unresolved_or_superseded_target_conversation_rejected(db_session, status, superseded):
    conversation = _conversation(db_session, status=status, superseded=superseded)
    target, _ = _email(db_session, conversation)
    with pytest.raises(AnalysisDomainError):
        _selection(db_session, target)


def test_target_body_missing_is_bounded_and_no_fabrication(db_session):
    conversation = _conversation(db_session)
    target, _ = _email(db_session, conversation, body=None)
    with pytest.raises(NoAnalyzableBody) as error:
        _selection(db_session, target)
    assert error.value.code == "no_analyzable_body"


def test_budget_target_first_and_prior_shared_without_metadata_charge(db_session):
    conversation = _conversation(db_session)
    old, _ = _email(db_session, conversation, body="oldbody", date=DAY - timedelta(days=2))
    recent, _ = _email(db_session, conversation, body="recentbody", date=DAY - timedelta(days=1))
    target, _ = _email(db_session, conversation, body="target", subject="x" * 998)
    selected = _selection(db_session, target, max_body_chars=12).selected_messages
    assert [(row.source_record_id, row.body_excerpt) for row in selected] == [
        (target.id, "target"), (recent.id, "recent"), (old.id, "")]
    assert len(selected[0].subject) == 998
    assert sum(len(row.body_excerpt) for row in selected) == 12


def test_oversized_target_and_full_body_digest_detects_hidden_change(db_session):
    conversation = _conversation(db_session)
    prior, _ = _email(db_session, conversation, body="prior")
    target, email = _email(db_session, conversation, body="A" * 30000 + "x")
    first = _selection(db_session, target)
    assert len(first.selected_messages[0].body_excerpt) == 30000
    assert first.selected_messages[1].source_record_id == prior.id
    assert first.selected_messages[1].body_excerpt == ""
    email.normalized_body = "A" * 30000 + "y"
    db_session.flush()
    second = _selection(db_session, target)
    assert first.selected_messages[0].body_excerpt == second.selected_messages[0].body_excerpt
    assert first.input_digest != second.input_digest


@pytest.mark.parametrize("changes", [
    {"max_prior": 7}, {"max_body_chars": 30001}, {"max_prior": -1},
    {"max_body_chars": 0}, {"contract_version": 0}, {"policy_version": 0},
])
def test_rejects_widening_or_invalid_limits(db_session, changes):
    conversation = _conversation(db_session)
    target, _ = _email(db_session, conversation)
    with pytest.raises(AnalysisDomainError):
        _selection(db_session, target, **changes)


def test_digest_stability_and_changes_to_selected_body_metadata_versions_order(db_session):
    conversation = _conversation(db_session)
    prior, prior_email = _email(db_session, conversation, body="one", date=DAY - timedelta(days=1))
    target, email = _email(db_session, conversation, body="two")
    first = _selection(db_session, target)
    assert first == _selection(db_session, target)
    email.normalized_body = "three"
    db_session.flush()
    changed_body = _selection(db_session, target)
    assert first.input_digest != changed_body.input_digest
    email.subject = "Different"
    db_session.flush()
    assert changed_body.input_digest != _selection(db_session, target).input_digest
    assert _selection(db_session, target, contract_version=2).input_digest != _selection(db_session, target).input_digest
    assert _selection(db_session, target, policy_version=2).input_digest != _selection(db_session, target).input_digest
    prior_email.sent_at = DAY + timedelta(days=1)
    db_session.flush()
    assert prior.id not in [row.source_record_id for row in _selection(db_session, target).selected_messages]
    assert first.input_digest != _selection(db_session, target).input_digest


def test_selector_does_not_flush_write_commit_or_rollback(db_session):
    conversation = _conversation(db_session)
    target, _ = _email(db_session, conversation)
    writes = []
    commits = []
    rollbacks = []

    def observe(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", observe)
    event.listen(db_session, "before_commit", lambda _: commits.append(True))
    event.listen(db_session, "after_rollback", lambda _: rollbacks.append(True))
    try:
        db_session.add(SourceRecord(source_type="manual_note", source_system_scope="manual", provenance="test"))
        _selection(db_session, target)
        assert not writes and not commits and not rollbacks
        assert bool(db_session.new)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", observe)


def test_evidence_validates_original_body_and_disclosed_prefix():
    body = "alpha question? omega"
    selected = SelectedMessage(1, "target", body[:15], sha256(body.encode()).hexdigest(),
                               None, (), None, None)
    candidate = _span(1, body, 6, 15)
    validate_evidence(candidate, body, selected)
    for invalid in (
        EvidenceCandidate(2, 6, 15, candidate.span_digest, candidate.exact_text),
        EvidenceCandidate(1, 6, 15, candidate.span_digest, "not a match"),
        EvidenceCandidate(1, 6, 15, "0" * 64, candidate.exact_text),
        _span(1, body, 6, 16),
    ):
        with pytest.raises(AnalysisDomainError):
            validate_evidence(invalid, body, selected)
    with pytest.raises(AnalysisDomainError):
        validate_evidence(candidate, body + " changed", selected)
    with pytest.raises(AnalysisDomainError):
        EvidenceCandidate(1, 3, 3, "0" * 64, "x")


def test_conservative_quote_classification_and_current_question():
    plain = "Can you send it?"
    candidate = _span(1, plain, 0, len(plain))
    selected = SelectedMessage(1, "target", plain, sha256(plain.encode()).hexdigest(),
                               None, (), None, None)
    input_value = AnalysisInput("imap:one", 1, 1, 1, (selected,), "a" * 64)
    assert classify_quote(plain, candidate) == "new"
    assert current_question_eligible(input_value, candidate, plain)
    assert not current_question_eligible(input_value, _span(2, plain, 0, len(plain)), plain)
    quoted = "> Can you send it?"
    assert classify_quote(quoted, _span(1, quoted, 2, len(quoted))) == "quoted"
    historical = "New text\n-----Original Message-----\nCan you send it?"
    start = historical.index("Can")
    assert classify_quote(historical, _span(1, historical, start, len(historical))) == "quoted"
    ambiguous = "From: Alice\nCan you send it?"
    start = ambiguous.index("Can")
    assert classify_quote(ambiguous, _span(1, ambiguous, start, len(ambiguous))) == "ambiguous"


@pytest.mark.parametrize("field,value", [
    ("response_needed", "maybe"), ("commercial_risk", "critical"), ("priority", "immediate"),
])
def test_inference_enums_are_bounded(field, value):
    with pytest.raises(AnalysisDomainError):
        AnalysisCandidates(**{field: value})


def test_valid_candidates_and_immutable_collections():
    evidence = _span(1, "Question?", 0, 9)
    candidates = AnalysisCandidates(
        summary="A derived summary", facts=(FactCandidate("question", "?", evidence),),
        inferences=(InferenceCandidate("risk", "low", (0,)),),
        proposals=(ProposalCandidate("reply", "draft", (0,), evidence),),
        questions=(QuestionCandidate("Question?", evidence, "new"),),
        commitments=(CommitmentCandidate("promise", "self", "none", None, None, evidence, True),),
        tasks=(TaskCandidate("follow up", None, (0,)),),
        next_steps=(NextStepCandidate("reply", None, (0,)),),
        response_needed="uncertain", commercial_risk="unknown", priority="normal",
        context_mentions=(ContextMention("company", "ACME", evidence),),
    )
    assert candidates.facts[0].evidence == evidence
    with pytest.raises(FrozenInstanceError):
        candidates.summary = "changed"
    with pytest.raises(AnalysisDomainError):
        AnalysisCandidates(facts=[candidates.facts[0]])
    assert "approval" not in {field.name for field in fields(AnalysisCandidates)}
    assert "execution" not in {field.name for field in fields(AnalysisCandidates)}


@pytest.mark.parametrize("certainty,due,expression,valid", [
    ("exact", DAY, None, True), ("exact", None, None, False),
    ("resolved_relative", DAY, "tomorrow", True),
    ("resolved_relative", DAY, None, False), ("resolved_relative", None, "tomorrow", False),
    ("uncertain", None, "tomorrow", True), ("uncertain", DAY, "tomorrow", False),
    ("none", None, None, True), ("none", DAY, None, False),
    ("invalid", None, None, False),
])
def test_commitment_date_semantics(certainty, due, expression, valid):
    evidence = _span(1, "promise", 0, 7)
    make = lambda: CommitmentCandidate("promise", "counterparty", certainty,
                                       expression, due, evidence, True)
    if valid:
        assert make().date_certainty == certainty
    else:
        with pytest.raises(AnalysisDomainError):
            make()


def test_candidate_bounds_question_evidence_and_support_shape():
    evidence = _span(1, "Question?", 0, 9)
    for invalid in ("", "x" * 4001):
        with pytest.raises(AnalysisDomainError):
            AnalysisCandidates(summary=invalid)
    assert len(AnalysisCandidates(summary="x" * 4000).summary) == 4000
    with pytest.raises(AnalysisDomainError):
        FactCandidate("fact", "x" * 256, evidence)
    with pytest.raises(AnalysisDomainError):
        QuestionCandidate("Different?", evidence, "new")
    with pytest.raises(AnalysisDomainError):
        QuestionCandidate("Question?", evidence, "unclear")
    with pytest.raises(AnalysisDomainError):
        InferenceCandidate("risk", "low", (-1,))
    with pytest.raises(AnalysisDomainError):
        ContextMention("unknown", "ACME", evidence)
    with pytest.raises(AnalysisDomainError):
        CommitmentCandidate("promise", "someone", "none", None, None, evidence, True)
