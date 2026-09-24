"""Synthetic Phase 4E orchestration tests; no real provider or external account."""

from dataclasses import fields
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import AISettings
from app.domain.email_analysis import (
    AnalysisCandidates, AnalysisInput, AnalyticalSignalCandidate,
    CommitmentCandidate, ContextMention, EvidenceCandidate, FactCandidate,
    InferenceCandidate, NextStepCandidate, ProposalCandidate, QuestionCandidate,
    SupportRef, TaskCandidate, select_analysis_input,
)
from app.integrations.openai_analysis import OpenAIAnalysis
from app.persistence.database import make_session_factory
from app.persistence.models import (
    ActionProposal, Alert, AnalysisDerivationLink, AnalysisOperationalLink, AnalysisRun,
    AnalysisSourceEvidence, AnalysisSummary, ApprovalDecision, Base,
    Commitment, Conversation, ConversationMembership, EmailMessage, ExecutionResult,
    ExtractedFact, FactSourceEvidence, Inference, NextStep, OperationalEvidenceLink,
    Proposal, Question, SourceRecord, Task,
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


def _remote_output(*, body="Need a quote?"):
    evidence = {"message_alias": "m0", "start_offset": 0,
                "end_offset": len(body), "exact_text": body}
    return {"schema_version": 1, "summary": "A quote was requested.",
            "facts": [{"fact_type": "request", "value_reference": "quote",
                       "evidence": evidence}], "inferences": [], "proposals": [],
            "questions": [{"question_text": body, "evidence": evidence}],
            "commitments": [], "tasks": [], "next_steps": [],
            "response_needed": None, "commercial_risk": None,
            "priority": None, "context_mentions": []}


def _remote_response(payload):
    part = SimpleNamespace(type="output_text", text=json.dumps(payload))
    return SimpleNamespace(status="completed", output=[SimpleNamespace(
        type="message", role="assistant", content=[part])])


class _OfflineOpenAI:
    def __init__(self, outcome):
        self.outcome = outcome
        self.factory_calls = []
        self.calls = []
        self.credentials = []

    def get_secret(self, service, account):
        self.credentials.append((service, account))
        return "synthetic-test-key-only"

    def __call__(self, **kwargs):
        self.factory_calls.append(kwargs)
        return SimpleNamespace(responses=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcome() if callable(self.outcome) else self.outcome
        if isinstance(outcome, Exception):
            raise outcome
        return _remote_response(outcome)

    def adapter(self):
        return OpenAIAnalysis(AISettings(enabled=True,
                              base_url="https://eu.api.openai.com/v1"),
                              self, client_factory=self)


@pytest.fixture
def _fake_openai_module(monkeypatch):
    class ConnectionError(Exception):
        pass

    class TimeoutError(ConnectionError):
        pass

    class RateLimitError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        APITimeoutError=TimeoutError, APIConnectionError=ConnectionError,
        RateLimitError=RateLimitError, AuthenticationError=AuthenticationError))


def test_concrete_openai_completes_replays_and_forces_new_run(analysis_db, _fake_openai_module):
    target_id, _, _ = _seed(analysis_db)
    remote = _OfflineOpenAI(_remote_output())
    adapter = remote.adapter()
    first = analyze_email_in_thread(analysis_db, adapter, "imap:test", target_id)
    assert first.status == "completed" and len(remote.calls) == 1
    assert analyze_email_in_thread(analysis_db, adapter, "imap:test", target_id).status == "completed_replay"
    assert analyze_email_in_thread(analysis_db, adapter, "imap:test", target_id,
                                   request_mode="manual").status == "completed_replay"
    assert len(remote.calls) == len(remote.credentials) == 1
    second = analyze_email_in_thread(analysis_db, adapter, "imap:test", target_id,
                                     force_reanalysis=True)
    assert second.status == "completed" and second.run_id != first.run_id
    assert len(remote.calls) == len(remote.credentials) == 2
    with analysis_db() as session:
        assert [run.run_version for run in session.scalars(
            select(AnalysisRun).order_by(AnalysisRun.run_version))] == [1, 2]
        assert len(session.scalars(select(Question)).all()) == 2
        assert session.scalars(select(ActionProposal)).all() == []


@pytest.mark.parametrize("outcome, expected", [
    (RuntimeError("provider body and synthetic-test-key-only"), "provider_failure"),
    ({"schema_version": 1}, "provider_failure"),
])
def test_concrete_openai_failure_is_bounded_and_retryable(
        analysis_db, _fake_openai_module, outcome, expected, caplog):
    target_id, _, _ = _seed(analysis_db)
    remote = _OfflineOpenAI(outcome)
    caplog.set_level(logging.DEBUG)
    result = analyze_email_in_thread(analysis_db, remote.adapter(), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("failed_retryable", expected)
    assert len(remote.calls) == 1
    assert "synthetic-test-key-only" not in repr(result)
    assert "provider body" not in repr(result)
    assert "synthetic-test-key-only" not in caplog.text
    assert "provider body" not in caplog.text
    assert _runs(analysis_db)[0].failure_code == expected
    with analysis_db() as session:
        assert session.scalars(select(AnalysisSourceEvidence)).all() == []
    retry = _OfflineOpenAI(_remote_output())
    again = analyze_email_in_thread(analysis_db, retry.adapter(), "imap:test", target_id)
    assert again.status == "completed" and again.run_id != result.run_id
    assert len(retry.calls) == 1


def test_concrete_openai_stale_source_and_provider_outside_write_transaction(
        analysis_db, _fake_openai_module):
    target_id, _, _ = _seed(analysis_db)

    def mutate_after_call():
        with analysis_db.kw["bind"].connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql("ROLLBACK")
        with analysis_db() as session, session.begin():
            email = session.scalar(select(EmailMessage).where(
                EmailMessage.source_record_id == target_id))
            email.normalized_body = "Changed after provider call"
        return _remote_output()

    remote = _OfflineOpenAI(mutate_after_call)
    result = analyze_email_in_thread(analysis_db, remote.adapter(), "imap:test", target_id)
    assert (result.status, result.failure_code) == ("stale_retryable", "input_changed")
    assert len(remote.calls) == 1
    with analysis_db() as session:
        for model in (AnalysisSourceEvidence, ExtractedFact, Question):
            assert session.scalars(select(model)).all() == []


def test_concrete_openai_no_body_skips_client_and_credentials(analysis_db, _fake_openai_module):
    target_id, _, _ = _seed(analysis_db, body=None)
    remote = _OfflineOpenAI(_remote_output())
    result = analyze_email_in_thread(analysis_db, remote.adapter(), "imap:test", target_id)
    assert result.status == "no_analyzable_body"
    assert remote.calls == remote.factory_calls == remote.credentials == []
    assert _runs(analysis_db) == []


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


def test_six_prior_and_thirty_thousand_character_disclosure_limit(analysis_db):
    with analysis_db() as session, session.begin():
        conversation = Conversation(account_scope="imap:test", stable_key=str(uuid4()),
                                    legacy_status="resolved", provenance="test")
        session.add(conversation)
        session.flush()
        for index in range(8):
            source = SourceRecord(source_type="email_message", source_system_scope="imap:test",
                                  stable_external_id=str(uuid4()), provenance="test")
            session.add(source)
            session.flush()
            session.add_all((
                EmailMessage(source_record_id=source.id, normalized_body=str(index) * 10000,
                             subject=f"Prior {index}", provenance="test"),
                ConversationMembership(conversation_id=conversation.id,
                                       source_record_id=source.id, evidence_type="test",
                                       evidence_reference="test"),
            ))
        target = SourceRecord(source_type="email_message", source_system_scope="imap:test",
                              stable_external_id=str(uuid4()), provenance="test")
        session.add(target)
        session.flush()
        target_id = target.id
        session.add_all((
            EmailMessage(source_record_id=target_id, normalized_body="T" * 10000,
                         subject="Target", provenance="test"),
            ConversationMembership(conversation_id=conversation.id,
                                   source_record_id=target_id, evidence_type="test",
                                   evidence_reference="test"),
        ))

    class CaptureProvider:
        seen = None

        def analyze(self, analysis_input):
            self.seen = analysis_input
            return AnalysisCandidates()

    provider = CaptureProvider()
    assert analyze_email_in_thread(analysis_db, provider, "imap:test", target_id).status == "completed"
    messages = provider.seen.selected_messages
    assert len(messages) == 7
    assert messages[0].body_excerpt == "T" * 10000
    assert [item.subject for item in messages[1:]] == [f"Prior {index}" for index in range(7, 1, -1)]
    assert sum(len(item.body_excerpt) for item in messages) == 30000
    assert [len(item.body_excerpt) for item in messages[1:]] == [10000, 10000, 0, 0, 0, 0]


def test_oversized_target_discloses_no_prior_body_but_keeps_metadata(analysis_db):
    target_id, _, prior_id = _seed(analysis_db, body="T" * 35000,
                                   prior_body="sensitive prior body")

    class CaptureProvider:
        seen = None

        def analyze(self, analysis_input):
            self.seen = analysis_input
            return AnalysisCandidates()

    provider = CaptureProvider()
    assert analyze_email_in_thread(analysis_db, provider, "imap:test", target_id).status == "completed"
    target, prior = provider.seen.selected_messages
    assert len(target.body_excerpt) == 30000
    assert prior.source_record_id == prior_id and prior.subject == "Prior"
    assert prior.body_excerpt == ""
    assert "sensitive prior body" not in repr(provider.seen)


def test_phase4_synthetic_thread_end_to_end_with_append_only_reanalysis(analysis_db):
    body = ("Please quote Project Blue?\n"
            "I promise to review the quotation.\n")
    target_id, _, prior_id = _seed(analysis_db, body=body,
                                   prior_body="Earlier inquiry for Project Blue.")

    def span(text):
        start = body.index(text)
        return EvidenceCandidate(target_id, start, start + len(text),
                                 sha256(text.encode("utf-8")).hexdigest(), text)

    question = span("Please quote Project Blue?")
    promise = span("I promise to review the quotation.")
    mention = span("Project Blue")
    candidates = AnalysisCandidates(
        summary="A quotation is requested for Project Blue; review was promised.",
        facts=(FactCandidate("quotation_request", "Project Blue", question),),
        inferences=(InferenceCandidate("commercial_intent", "active_request",
                                       (SupportRef("fact", 0),)),),
        proposals=(ProposalCandidate("prepare_offer", "Project Blue quotation",
                                     (SupportRef("inference", 0),)),),
        questions=(QuestionCandidate(question.exact_text, question, "new"),),
        commitments=(CommitmentCandidate("Review the quotation", "self", "none",
                                         None, None, promise, True),),
        tasks=(TaskCandidate("Prepare quotation", None,
                             (SupportRef("proposal", 0),)),),
        next_steps=(NextStepCandidate("Share quotation", None,
                                      (SupportRef("proposal", 0),)),),
        response_needed=AnalyticalSignalCandidate("yes", (SupportRef("fact", 0),)),
        commercial_risk=AnalyticalSignalCandidate("low", (SupportRef("fact", 0),)),
        priority=AnalyticalSignalCandidate("normal", (SupportRef("fact", 0),)),
        context_mentions=(ContextMention("work", "Project Blue", mention),),
    )
    fake = FakeAIService(default_output=candidates)
    first = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id)
    assert first.status == "completed" and len(fake.calls) == 1
    with analysis_db() as session:
        run = session.get(AnalysisRun, first.run_id)
        assert run.status == "completed" and run.target_source_record_id == target_id
        assert len(session.scalars(select(AnalysisSourceEvidence)).all()) == 3
        assert len(session.scalars(select(FactSourceEvidence)).all()) == 3
        assert len(session.scalars(select(Inference)).all()) == 4
        assert len(session.scalars(select(Proposal)).all()) == 3
        assert len(session.scalars(select(AnalysisOperationalLink)).all()) == 4
        assert len(session.scalars(select(OperationalEvidenceLink)).all()) == 6
        assert session.scalar(select(AnalysisSummary)).summary_text == candidates.summary
        assert session.scalar(select(Question)).state == "detected"
        assert session.scalar(select(Commitment)).state == "confirmed"
        assert session.scalar(select(Task)).state == "proposed"
        assert session.scalar(select(NextStep)).state == "proposed"
        assert session.scalars(select(ActionProposal)).all() == []
        assert prior_id in [item.source_record_id for item in
                            select_analysis_input(session, "imap:test", target_id).selected_messages]
    assert analyze_email_in_thread(analysis_db, fake, "imap:test", target_id).status == "completed_replay"
    assert len(fake.calls) == 1
    second = analyze_email_in_thread(analysis_db, fake, "imap:test", target_id,
                                     force_reanalysis=True)
    assert second.status == "completed" and len(fake.calls) == 2
    with analysis_db() as session:
        newer = session.get(AnalysisRun, second.run_id)
        assert newer.supersedes_run_id == first.run_id
        assert len(session.scalars(select(Question)).all()) == 2
        assert len(session.scalars(select(AnalysisSummary)).all()) == 2
