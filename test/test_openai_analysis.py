"""Offline contract tests for the disabled-by-default Phase 5C adapter."""

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import inspect
import logging
import sys
import threading
from types import SimpleNamespace

import pytest

from app.config import AISettings
from app.domain.email_analysis import AnalysisCandidates, AnalysisInput, SelectedMessage
from app.integrations.openai_analysis import OpenAIAnalysis, OpenAIAnalysisError
from app.security.activation import CommercialActivationGate


class FakeOwnership:
    def __init__(self, owned=True):
        self.is_owner = owned


def _enabled_gate():
    gate = CommercialActivationGate()
    gate.enable()
    return gate


class APIConnectionError(Exception):
    pass


class APITimeoutError(APIConnectionError):
    pass


class APIStatusError(Exception):
    def __init__(self, status_code, code=None, retry_after=None):
        super().__init__("raw provider error: synthetic-secret-and-body")
        self.status_code = status_code
        self.code = code
        self.response = SimpleNamespace(headers={} if retry_after is None else
                                        {"retry-after": retry_after})


class RateLimitError(APIStatusError):
    pass


class AuthenticationError(APIStatusError):
    pass


@pytest.fixture(autouse=True)
def fake_openai_module(monkeypatch):
    module = SimpleNamespace(OpenAI=lambda **kwargs: None,
                             APIConnectionError=APIConnectionError,
                             APITimeoutError=APITimeoutError,
                             RateLimitError=RateLimitError,
                             AuthenticationError=AuthenticationError)
    monkeypatch.setitem(sys.modules, "openai", module)


def _input(body="Need a quote?", prior="Earlier commercial context."):
    selected = []
    for source_id, role, text in ((101, "target", body), (202, "prior", prior)):
        selected.append(SelectedMessage(source_id, role, text,
                                        sha256(text.encode()).hexdigest(),
                                        "person@example.test", (), "Commercial topic",
                                        datetime(2026, 9, 24, tzinfo=timezone.utc)))
    return AnalysisInput("imap:synthetic", 101, 1, 1, tuple(selected), "a" * 64)


def _empty():
    return {"schema_version": 1, "summary": None, "facts": [], "inferences": [],
            "proposals": [], "questions": [], "commitments": [], "tasks": [],
            "next_steps": [], "response_needed": None, "commercial_risk": None,
            "priority": None, "context_mentions": []}


def _response(payload=None, *, status="completed", part_type="output_text"):
    part = SimpleNamespace(type=part_type, text=json.dumps(_empty() if payload is None else payload),
                           refusal="synthetic refusal")
    message = SimpleNamespace(type="message", role="assistant", content=[part])
    return SimpleNamespace(status=status, output=[message], incomplete_details=None)


class FakeCredentials:
    def __init__(self, secret="synthetic-secret-and-body", *, fail=False):
        self.secret = secret
        self.fail = fail
        self.calls = []

    def get_secret(self, service, account):
        self.calls.append((service, account))
        if self.fail:
            raise RuntimeError("synthetic-secret-and-body")
        return self.secret


class FakeResponses:
    def __init__(self, outcomes=None):
        self.outcomes = list(outcomes or [_response()])
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self.outcomes.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeFactory:
    def __init__(self, outcomes=None):
        self.responses = FakeResponses(outcomes)
        self.kwargs = []

    def __call__(self, **kwargs):
        self.kwargs.append(kwargs)
        return SimpleNamespace(responses=self.responses)


def _adapter(*, settings=None, credentials=None, factory=None, **kwargs):
    kwargs.setdefault("ownership", FakeOwnership())
    kwargs.setdefault("commercial_gate", _enabled_gate())
    return OpenAIAnalysis(settings or AISettings(enabled=True,
                            base_url="https://eu.api.openai.com/v1"),
                          credentials or FakeCredentials(),
                          client_factory=factory or FakeFactory(), **kwargs)


def test_disabled_does_not_touch_credentials_or_client():
    credentials, factory = FakeCredentials(), FakeFactory()
    adapter = _adapter(settings=AISettings(), credentials=credentials, factory=factory)
    with pytest.raises(OpenAIAnalysisError, match="disabled"):
        adapter.analyze(_input())
    assert credentials.calls == factory.kwargs == factory.responses.calls == []


@pytest.mark.parametrize("ownership, gate, code", [
    (None, None, "operational_ownership_required"),
    (FakeOwnership(False), None, "operational_ownership_required"),
    (FakeOwnership(True), CommercialActivationGate(), "commercial_activation_required"),
])
def test_missing_ownership_or_commercial_authorization_blocks_before_credentials(
        ownership, gate, code):
    credentials, factory = FakeCredentials(), FakeFactory()
    adapter = OpenAIAnalysis(AISettings(enabled=True), credentials,
                             ownership=ownership, commercial_gate=gate,
                             client_factory=factory)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.analyze(_input())
    assert caught.value.code == code
    assert credentials.calls == factory.kwargs == factory.responses.calls == []


def test_disabled_precedes_ownership_and_commercial_checks():
    credentials, factory = FakeCredentials(), FakeFactory()
    adapter = OpenAIAnalysis(AISettings(), credentials, client_factory=factory)
    with pytest.raises(OpenAIAnalysisError, match="disabled"):
        adapter.analyze(_input())
    assert credentials.calls == factory.kwargs == factory.responses.calls == []


@pytest.mark.parametrize("revoke", ["gate", "owner"])
def test_revocation_during_retry_delay_prevents_second_attempt(revoke):
    gate, owner = _enabled_gate(), FakeOwnership()
    factory = FakeFactory([APIConnectionError("synthetic-secret-and-body"), _response()])

    def sleep(_delay):
        if revoke == "gate":
            gate.disable()
        else:
            owner.is_owner = False

    adapter = _adapter(factory=factory, commercial_gate=gate, ownership=owner, sleep=sleep)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.analyze(_input())
    assert caught.value.code == ("commercial_activation_required" if revoke == "gate"
                                 else "operational_ownership_required")
    assert len(factory.responses.calls) == 1
    assert "synthetic-secret-and-body" not in str(caught.value)


def test_revocation_after_client_creation_prevents_first_attempt():
    gate, owner = _enabled_gate(), FakeOwnership()
    factory = FakeFactory()

    def revoke_during_factory(**kwargs):
        result = factory(**kwargs)
        gate.disable()
        return result

    adapter = OpenAIAnalysis(AISettings(enabled=True,
                             base_url="https://eu.api.openai.com/v1"), FakeCredentials(),
                             client_factory=revoke_during_factory, commercial_gate=gate,
                             ownership=owner)
    with pytest.raises(OpenAIAnalysisError, match="commercial_activation_required"):
        adapter.analyze(_input())
    assert len(factory.kwargs) == 1
    assert factory.responses.calls == []


@pytest.mark.parametrize("credentials, expected", [
    (FakeCredentials(None), "credential_missing"),
    (FakeCredentials(fail=True), "credential_unavailable"),
])
def test_credential_failure_is_bounded(credentials, expected):
    factory = FakeFactory()
    adapter = _adapter(credentials=credentials, factory=factory)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.analyze(_input())
    assert caught.value.code == expected
    assert "synthetic-secret-and-body" not in str(caught.value)
    assert "synthetic-secret-and-body" not in repr(adapter)
    assert factory.kwargs == []


def test_request_uses_responses_strict_schema_and_minimized_untrusted_input(caplog):
    caplog.set_level(logging.DEBUG)
    factory = FakeFactory()
    credentials = FakeCredentials()
    settings = AISettings(enabled=True, model="gpt-6-sol",
                          base_url="https://eu.api.openai.com/v1", max_output_tokens=900)
    result = _adapter(settings=settings, credentials=credentials, factory=factory).analyze(_input())
    assert isinstance(result, AnalysisCandidates)
    assert credentials.calls == [(settings.credential_service, settings.credential_account)]
    assert factory.kwargs[0]["max_retries"] == 0
    assert factory.kwargs[0]["base_url"] == settings.base_url
    assert factory.kwargs[0]["api_key"] == credentials.secret
    assert factory.kwargs[0]["timeout"] <= 60
    call = factory.responses.calls[0]
    assert call["model"] == "gpt-6-sol"
    assert call["max_output_tokens"] == 900
    assert call["store"] is False
    assert 0 < call["timeout"] <= 60
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert call["text"]["format"]["schema"]["additionalProperties"] is False
    assert not set(call) & {"tools", "tool_choice", "functions", "stream"}
    assert "Need a quote?" not in call["instructions"]
    assert "Need a quote?" in call["input"][0]["content"]
    assert call["input"][0]["role"] == "user"
    assert json.loads(call["input"][0]["content"])["messages"][0]["message_alias"] == "m0"
    assert json.loads(call["input"][0]["content"])["messages"][1]["message_alias"] == "m1"
    for forbidden in ("source_record_id", "account_scope", "input_digest",
                      "original_body_digest", "imap:synthetic", "synthetic-secret-and-body"):
        assert forbidden not in call["input"][0]["content"]
    assert "Need a quote?" not in caplog.text
    assert "synthetic-secret-and-body" not in caplog.text
    assert "Need a quote?" not in repr(result)


@pytest.mark.parametrize("response, code", [
    (_response(status="incomplete"), "provider_incomplete"),
    (_response(status="failed"), "invalid_output"),
    (_response(part_type="refusal"), "provider_refusal"),
    (_response(part_type="tool_call"), "invalid_output"),
    (_response({"schema_version": 1}), "invalid_output"),
])
def test_bad_response_fails_without_retry(response, code):
    factory = FakeFactory([response])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == code
    assert len(factory.responses.calls) == 1
    assert "synthetic refusal" not in str(caught.value)


def test_non_json_and_oversize_output_fail_closed():
    for text in ("{bad json", "x" * 160_001):
        response = _response()
        response.output[0].content[0].text = text
        factory = FakeFactory([response])
        with pytest.raises(OpenAIAnalysisError, match="invalid_output"):
            _adapter(factory=factory).analyze(_input())
        assert len(factory.responses.calls) == 1


@pytest.mark.parametrize("error, code", [
    (AuthenticationError(401), "provider_auth"),
    (APIStatusError(403), "provider_auth"),
    (APIStatusError(402), "provider_quota"),
    (RateLimitError(429, "insufficient_quota"), "provider_quota"),
    (RateLimitError(429, "billing_hard_limit_reached"), "provider_quota"),
    (APIStatusError(400), "provider_failure"),
])
def test_non_transient_errors_never_retry(error, code):
    factory = FakeFactory([error])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == code
    assert len(factory.responses.calls) == 1
    assert "synthetic-secret-and-body" not in str(caught.value)


@pytest.mark.parametrize("error", [
    APIConnectionError("synthetic-secret-and-body"),
    APITimeoutError("synthetic-secret-and-body"),
    RateLimitError(429, "rate_limit_exceeded"),
    RateLimitError(429),
    APIStatusError(429, "unrecognized_provider_code"),
    APIStatusError(503),
])
def test_transient_errors_retry_once(error):
    factory = FakeFactory([error, _response()])
    assert isinstance(_adapter(factory=factory, sleep=lambda _: None).analyze(_input()), AnalysisCandidates)
    assert len(factory.responses.calls) == 2
    assert factory.responses.calls[1]["timeout"] <= factory.responses.calls[0]["timeout"]


def test_second_transient_failure_stops_after_two_attempts():
    factory = FakeFactory([APIConnectionError("first"), APIConnectionError("second")])
    with pytest.raises(OpenAIAnalysisError, match="provider_transient_exhausted"):
        _adapter(factory=factory, sleep=lambda _: None).analyze(_input())
    assert len(factory.responses.calls) == 2


def test_second_unclassified_429_stops_after_two_attempts_without_leak():
    factory = FakeFactory([RateLimitError(429), RateLimitError(429)])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory, sleep=lambda _: None).analyze(_input())
    assert caught.value.code == "provider_transient_exhausted"
    assert len(factory.responses.calls) == 2
    assert "synthetic-secret-and-body" not in str(caught.value)


def test_retry_after_exceeding_budget_prevents_second_attempt():
    factory = FakeFactory([RateLimitError(429, None, "120")])
    with pytest.raises(OpenAIAnalysisError, match="provider_transient_exhausted"):
        _adapter(factory=factory, sleep=lambda _: None).analyze(_input())
    assert len(factory.responses.calls) == 1


def test_soft_deadline_caps_next_attempt_timeout_and_prevents_late_retry():
    current = [0.0]
    def clock():
        return current[0]
    def sleep(delay):
        current[0] += delay
    class AdvancingResponses(FakeResponses):
        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                current[0] += 30.0
                raise APIConnectionError("synthetic")
            return _response()
    factory = FakeFactory()
    factory.responses = AdvancingResponses()
    assert isinstance(_adapter(factory=factory, clock=clock, sleep=sleep).analyze(_input()), AnalysisCandidates)
    assert factory.responses.calls[1]["timeout"] < 30
    current[0] = 0
    factory = FakeFactory()
    factory.responses = AdvancingResponses()
    def exhaust(_):
        current[0] = 60
    with pytest.raises(OpenAIAnalysisError):
        _adapter(factory=factory, clock=clock, sleep=exhaust).analyze(_input())
    assert len(factory.responses.calls) == 1


def test_second_concurrent_call_cannot_reach_client():
    started, release = threading.Event(), threading.Event()
    class BlockingResponses(FakeResponses):
        def create(self, **kwargs):
            self.calls.append(kwargs)
            started.set()
            assert release.wait(timeout=5)
            return _response()
    factory = FakeFactory()
    factory.responses = BlockingResponses()
    adapter = _adapter(factory=factory)
    results = []
    thread = threading.Thread(target=lambda: results.append(adapter.analyze(_input())))
    thread.start()
    assert started.wait(timeout=5)
    try:
        with pytest.raises(OpenAIAnalysisError, match="busy"):
            adapter.analyze(_input())
        assert len(factory.responses.calls) == 1
    finally:
        release.set()
        thread.join(timeout=5)
    assert len(results) == 1


def test_sensitive_content_and_bad_endpoint_never_touch_client():
    factory = FakeFactory()
    with pytest.raises(OpenAIAnalysisError, match="sensitive_content"):
        _adapter(factory=factory).analyze(_input(body="password = SyntheticSecret123"))
    assert factory.kwargs == []
    with pytest.raises(OpenAIAnalysisError, match="invalid_configuration"):
        _adapter(factory=factory, settings=AISettings(enabled=True,
                 base_url="https://evil.example/v1")).analyze(_input())
    with pytest.raises(OpenAIAnalysisError, match="invalid_configuration"):
        _adapter(factory=factory, settings=AISettings(enabled=True,
                 base_url="https://eu.api.openai.com/v1", max_retries=3)).analyze(_input())
    assert factory.kwargs == []


def _smoke_adapter(*, settings=None, credentials=None, factory=None, ownership=None,
                   commercial_gate=None, **kwargs):
    return OpenAIAnalysis(settings or AISettings(enabled=True,
                          base_url="https://eu.api.openai.com/v1"),
                          credentials or FakeCredentials(),
                          ownership=FakeOwnership() if ownership is None else ownership,
                          commercial_gate=commercial_gate,
                          client_factory=factory or FakeFactory(), **kwargs)


def test_smoke_has_no_content_parameters_and_commercial_entry_still_requires_gate():
    factory, credentials = FakeFactory(), FakeCredentials()
    adapter = _smoke_adapter(factory=factory, credentials=credentials)
    assert list(inspect.signature(adapter.smoke).parameters) == []
    with pytest.raises(TypeError):
        adapter.smoke(_input())
    with pytest.raises(OpenAIAnalysisError, match="commercial_activation_required"):
        adapter.analyze(_input())
    assert credentials.calls == factory.kwargs == factory.responses.calls == []


def test_smoke_fixed_projection_shared_schema_and_one_shot_without_gate_access():
    class ForbiddenGate:
        @property
        def is_enabled(self):
            pytest.fail("smoke inspected commercial gate")

        def enable(self):
            pytest.fail("smoke enabled commercial gate")

        def disable(self):
            pytest.fail("smoke disabled commercial gate")

    credentials, factory = FakeCredentials(), FakeFactory()
    settings = AISettings(enabled=True, model="gpt-6-sol",
                          base_url="https://eu.api.openai.com/v1", max_output_tokens=900)
    adapter = _smoke_adapter(settings=settings, credentials=credentials, factory=factory,
                             commercial_gate=ForbiddenGate())
    assert adapter.smoke() == "passed"
    assert credentials.calls == [(settings.credential_service, settings.credential_account)]
    assert factory.kwargs[0]["max_retries"] == 0
    assert factory.kwargs[0]["base_url"] == settings.base_url
    call = factory.responses.calls[0]
    assert call["model"] == settings.model
    assert call["store"] is False
    assert call["max_output_tokens"] == 900
    assert 0 < call["timeout"] <= 60
    assert call["text"]["format"]["strict"] is True
    assert call["text"]["format"]["schema"]["additionalProperties"] is False
    assert not set(call) & {"tools", "tool_choice", "functions", "stream"}
    assert call["input"] == [{"role": "user", "content": json.dumps({"messages": [{
        "message_alias": "m0", "role": "target", "body_excerpt":
        "This is a synthetic test message. Please confirm receipt of a sample catalogue request.",
    }]}, ensure_ascii=False, separators=(",", ":"))}]
    for forbidden in ("Need a quote?", "person@example.test", "imap:synthetic",
                      "synthetic:smoke", "source_record_id", "input_digest"):
        assert forbidden not in call["input"][0]["content"]
    with pytest.raises(OpenAIAnalysisError, match="smoke_already_used"):
        adapter.smoke()
    assert len(factory.responses.calls) == 1


@pytest.mark.parametrize("settings, ownership, code", [
    (AISettings(), FakeOwnership(), "disabled"),
    (AISettings(enabled=True), FakeOwnership(False), "operational_ownership_required"),
])
def test_smoke_preflight_fails_before_secret_or_client(settings, ownership, code):
    credentials, factory = FakeCredentials(), FakeFactory()
    adapter = _smoke_adapter(settings=settings, ownership=ownership,
                             credentials=credentials, factory=factory)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.smoke()
    assert caught.value.code == code
    assert credentials.calls == factory.kwargs == factory.responses.calls == []


def test_smoke_revalidates_ownership_after_client_construction():
    ownership, factory = FakeOwnership(), FakeFactory()

    def release_during_factory(**kwargs):
        result = factory(**kwargs)
        ownership.is_owner = False
        return result

    adapter = OpenAIAnalysis(AISettings(enabled=True,
                             base_url="https://eu.api.openai.com/v1"), FakeCredentials(),
                             ownership=ownership, client_factory=release_during_factory)
    with pytest.raises(OpenAIAnalysisError, match="operational_ownership_required"):
        adapter.smoke()
    assert len(factory.kwargs) == 1
    assert factory.responses.calls == []


def test_smoke_ownership_loss_after_retry_delay_blocks_second_attempt():
    ownership = FakeOwnership()
    factory = FakeFactory([APIConnectionError("synthetic-secret-and-body"), _response()])

    def release(_delay):
        ownership.is_owner = False

    adapter = _smoke_adapter(factory=factory, ownership=ownership, sleep=release)
    with pytest.raises(OpenAIAnalysisError, match="operational_ownership_required"):
        adapter.smoke()
    assert len(factory.responses.calls) == 1


def test_smoke_provider_errors_are_bounded_and_do_not_leak():
    factory = FakeFactory([APIStatusError(403)])
    adapter = _smoke_adapter(factory=factory)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.smoke()
    assert caught.value.code == "provider_auth"
    assert "synthetic-secret-and-body" not in str(caught.value) + repr(adapter)
    with pytest.raises(OpenAIAnalysisError, match="smoke_already_used"):
        adapter.smoke()
