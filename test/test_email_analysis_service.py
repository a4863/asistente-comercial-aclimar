"""Synthetic Phase 4E orchestration tests; no real provider or external account."""

from dataclasses import fields
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.email_analysis import (
    AnalysisCandidates, AnalysisInput, EvidenceCandidate, FactCandidate,
    QuestionCandidate, select_analysis_input,
)
from app.persistence.database import make_session_factory
from app.persistence.models import (
    ActionProposal, Alert, AnalysisDerivationLink, AnalysisRun,
    AnalysisSourceEvidence, AnalysisSummary, ApprovalDecision, Base,
    Conversation, ConversationMembership, EmailMessage, ExecutionResult,
    ExtractedFact, Question, SourceRecord,
)
from app.persistence.repositories import (
    AnalysisRepository, AnalysisRepositoryError,
)
from app.services.email_analysis import (
    FakeAIService, analyze_email_in_thread,
)


@pytest.fixture
def analysis_db(isolated_tmp_path):
    factory = make_session_factory(f"sqlite:///{isolated_tmp_path / 'analysis.db'}")
    engine = factory.kw["bind"]
    Base.metadata.create_all(engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _seed(factory, *, body="Need a quote?", prior_body="absent"):
    with factory() as session, session.begin():
        conversation = Conversation(account_scope="imap:test", stable_key=str(uuid4()),
                                    legacy_status="resolved", provenance="test")
        session.add(conversation)
        session.flush()
        if prior_body != "absent":
            prior = SourceRecord(source_type="email_message", source_system_scope="imap:test",
                                 stable_external_id=str(uuid4()), provenance="test")
            session.add(prior)
            session.flush()
            prior_id = prior.id
            session.add_all((
                EmailMessage(source_record_id=prior_id, normalized_body=prior_body,
                             subject="Prior", provenance="test"),
                ConversationMembership(conversation_id=conversation.id,
                                       source_record_id=prior_id, evidence_type="test",
                                       evidence_reference="test"),
            ))
        else:
            prior_id = None
        target = SourceRecord(source_type="email_message", source_system_scope="imap:test",
                              stable_external_id=str(uuid4()), provenance="test")
        session.add(target)
        session.flush()
        target_id = target.id
        conversation_id = conversation.id
        session.add_all((
            EmailMessage(source_record_id=target_id, normalized_body=body,
                         subject="Request", provenance="test"),
            ConversationMembership(conversation_id=conversation_id,
                                   source_record_id=target_id, evidence_type="test",
                                   evidence_reference="test"),
        ))
    return target_id, conversation_id, prior_id


def _output(target_id, text="Need a quote?"):
    evidence = EvidenceCandidate(target_id, 0, len(text),
                                 sha256(text.encode("utf-8")).hexdigest(), text)
    return AnalysisCandidates(
        summary="A quote is requested.",
        facts=(FactCandidate("request", "quote", evidence),),
        questions=(QuestionCandidate(text, evidence, "new"),),
    )


def _runs(factory):
    with factory() as session:
        return session.scalars(select(AnalysisRun).order_by(AnalysisRun.run_version)).all()


def test_analysis_orchestrates_completion_replay_manual_and_force(analysis_db):
    target_id, _, _ = _seed(analysis_db)
    fake = FakeAIService(default_output=_output(target_id))
    first = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id)
    assert first.status == "completed" and first.run_id is not None
    assert len(fake.calls) == 1
    assert analyze_email_in_thread(analysis_db, fake, "imap:test", target_id).status == "completed_replay"
    assert analyze_email_in_thread(analysis_db, fake, "imap:test", target_id,
                                   request_mode="manual").status == "completed_replay"
    assert len(fake.calls) == 1
    second = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id,
                                     force_reanalysis=True)
    assert second.status == "completed" and second.run_id != first.run_id
    assert len(fake.calls) == 2
    runs = _runs(analysis_db)
    assert [run.run_version for run in runs] == [1, 2]
    assert runs[1].supersedes_run_id == runs[0].id
    with analysis_db() as session:
        assert len(session.scalars(select(ExtractedFact)).all()) == 4
        assert len(session.scalars(select(Question)).all()) == 2
        assert len(session.scalars(select(AnalysisDerivationLink)).all()) == 4
        for model in (Alert, ActionProposal, ApprovalDecision, ExecutionResult):
            assert session.scalars(select(model)).all() == []


def test_matching_reserved_run_returns_in_progress_without_provider(analysis_db):
    target_id, conversation_id, _ = _seed(analysis_db)
    with analysis_db() as session, session.begin():
        analysis_input = select_analysis_input(session, "imap:test", target_id)
        AnalysisRepository(session).reserve_run(
            "imap:test", target_id, conversation_id, analysis_input.input_digest,
            1, 1, "automatic")
    fake = FakeAIService()
    result = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id)
    assert result.status == "in_progress" and fake.calls == []


def test_target_without_body_never_reserves_or_calls_provider(analysis_db):
    target_id, _, _ = _seed(analysis_db, body=None)
    fake = FakeAIService()
    result = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id)
    assert result.status == "no_analyzable_body"
    assert fake.calls == [] and _runs(analysis_db) == []


def test_provider_receives_only_canonical_input_and_no_write_lock(analysis_db):
    target_id, _, _ = _seed(analysis_db, body="Need a quote?\n" + "x" * 40000)

    class InspectingProvider:
        def analyze(self, analysis_input):
            assert type(analysis_input) is AnalysisInput
            assert {field.name for field in fields(analysis_input)} == {
                "account_scope", "target_source_record_id", "contract_version",
                "policy_version", "selected_messages", "input_digest"}
            assert sum(len(item.body_excerpt) for item in analysis_input.selected_messages) <= 30000
            assert len(analysis_input.selected_messages[0].body_excerpt) == 30000
            assert not hasattr(analysis_input, "session")
            assert not hasattr(analysis_input, "credentials")
            # A separate SQLite writer can acquire its lock during the provider call.
            with analysis_db.kw["bind"].connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                connection.exec_driver_sql("ROLLBACK")
            return AnalysisCandidates()

    result = analyze_email_in_thread(analysis_db, InspectingProvider(), "imap:test", target_id)
    assert result.status == "completed"


def test_fake_is_deterministic_and_records_only_safe_metadata(analysis_db):
    target_id, _, _ = _seed(analysis_db)
    with analysis_db() as session:
        analysis_input = select_analysis_input(session, "imap:test", target_id)
    output = _output(target_id)
    fake = FakeAIService({analysis_input.input_digest: output})
    assert fake.analyze(analysis_input) is output
    assert fake.analyze(analysis_input) is output
    assert fake.calls == [(analysis_input.input_digest, 1, 1)] * 2


def test_provider_exception_is_bounded_and_retryable(analysis_db):
    target_id, _, _ = _seed(analysis_db)

    class FailingProvider:
        def analyze(self, _analysis_input):
            raise RuntimeError("PRIVATE PROVIDER TEXT AND SECRET")

    result = analyze_email_in_thread(analysis_db, FailingProvider(), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("failed_retryable", "provider_failure")
    assert "PRIVATE" not in repr(result)
    run = _runs(analysis_db)[0]
    assert (run.status, run.failure_code) == ("failed_retryable", "provider_failure")
    assert "PRIVATE" not in repr(run.failure_code)


@pytest.mark.parametrize("malformed", [object(), "bad"])
def test_wrong_provider_output_is_invalid_output(analysis_db, malformed):
    target_id, _, _ = _seed(analysis_db)

    class MalformedProvider:
        def analyze(self, _analysis_input):
            return malformed

    result = analyze_email_in_thread(analysis_db, MalformedProvider(), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("failed_retryable", "invalid_output")
    with analysis_db() as session:
        assert session.scalars(select(AnalysisSourceEvidence)).all() == []


def test_domain_invalid_mutated_candidates_are_rejected(analysis_db):
    target_id, _, _ = _seed(analysis_db)
    output = AnalysisCandidates()
    object.__setattr__(output, "summary", "")
    result = analyze_email_in_thread(analysis_db, FakeAIService(default_output=output),
                                     "imap:test", target_id)
    assert (result.status, result.failure_code) == ("failed_retryable", "invalid_output")


class MutatingProvider:
    def __init__(self, factory, change, output=None):
        self.factory = factory
        self.change = change
        self.output = output if output is not None else AnalysisCandidates()

    def analyze(self, _analysis_input):
        with self.factory() as session, session.begin():
            self.change(session)
        return self.output


@pytest.mark.parametrize("change", ["body", "hidden_suffix", "subject",
                                     "recipients", "date", "membership"])
def test_changed_target_or_thread_is_stale_without_derivations(analysis_db, change):
    body = "Need a quote?" + ("x" * 40000 if change == "hidden_suffix" else "")
    target_id, conversation_id, _ = _seed(analysis_db, body=body)

    def mutate(session):
        email = session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == target_id))
        if change == "body":
            email.normalized_body = "changed body"
        elif change == "hidden_suffix":
            email.normalized_body = body[:-1] + "y"
        elif change == "subject":
            email.subject = "Changed"
        elif change == "recipients":
            email.recipient_addresses = '["new@example.test"]'
        elif change == "date":
            email.sent_at = datetime(2026, 9, 24, tzinfo=timezone.utc)
        else:
            replacement = Conversation(account_scope="imap:test", stable_key=str(uuid4()),
                                       legacy_status="resolved", provenance="test")
            session.add(replacement)
            session.flush()
            membership = session.scalar(select(ConversationMembership).where(
                ConversationMembership.source_record_id == target_id))
            membership.conversation_id = replacement.id

    result = analyze_email_in_thread(analysis_db, MutatingProvider(
        analysis_db, mutate, _output(target_id)), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("stale_retryable", "input_changed")
    run = _runs(analysis_db)[0]
    assert run.status == "stale_retryable" and run.conversation_id == conversation_id
    with analysis_db() as session:
        for model in (AnalysisSourceEvidence, AnalysisDerivationLink, ExtractedFact, Question):
            assert session.scalars(select(model)).all() == []


def test_metadata_only_prior_snapshot_and_later_change_are_stale(analysis_db):
    target_id, _, prior_id = _seed(analysis_db, prior_body=None)

    class PriorProvider:
        def analyze(self, analysis_input):
            assert len(analysis_input.selected_messages) == 2
            assert analysis_input.selected_messages[1].source_record_id == prior_id
            assert analysis_input.selected_messages[1].body_excerpt == ""
            with analysis_db() as session, session.begin():
                prior = session.scalar(select(EmailMessage).where(
                    EmailMessage.source_record_id == prior_id))
                prior.normalized_body = "new prior body"
            return AnalysisCandidates()

    result = analyze_email_in_thread(analysis_db, PriorProvider(), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("stale_retryable", "input_changed")


def test_metadata_only_prior_completes_without_evidence(analysis_db):
    target_id, _, prior_id = _seed(analysis_db, prior_body=None)
    fake = FakeAIService()
    result = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id)
    assert result.status == "completed"
    assert len(fake.calls) == 1
    with analysis_db() as session:
        assert session.scalar(select(EmailMessage.normalized_body).where(
            EmailMessage.source_record_id == prior_id)) is None
        assert session.scalars(select(AnalysisSourceEvidence)).all() == []


def test_repository_persistence_failure_rolls_back_then_marks_retryable(analysis_db, monkeypatch):
    target_id, _, _ = _seed(analysis_db)

    def fail_after_insert(self, run_id, *_args):
        self.session.add(AnalysisSummary(
            analysis_run_id=run_id, summary_text="partial",
            summary_digest=sha256(b"partial").hexdigest()))
        self.session.flush()
        raise AnalysisRepositoryError("persistence_failure")

    monkeypatch.setattr(AnalysisRepository, "complete_run", fail_after_insert)
    result = analyze_email_in_thread(analysis_db, FakeAIService(), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("failed_retryable", "persistence_failure")
    assert _runs(analysis_db)[0].status == "failed_retryable"
    with analysis_db() as session:
        assert session.scalars(select(AnalysisSummary)).all() == []
