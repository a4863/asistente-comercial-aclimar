"""Offline contract tests for the disabled-by-default Phase 5C adapter."""

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import inspect
import logging
import ssl
import sys
import threading
from types import SimpleNamespace

import httpx2
import httpcore2
import idna
import openai as installed_openai
import pydantic
import pydantic_core
import pytest

from app.config import AISettings
from app.domain.email_analysis import AnalysisCandidates, AnalysisInput, SelectedMessage
from app.integrations.ai_schema import project_analysis_input, response_schema
from app.integrations.openai_analysis import (
    OpenAIAnalysis, OpenAIAnalysisError, _INSTRUCTIONS, _fixed_smoke_input,
)
from app.security.activation import CommercialActivationGate


class FakeOwnership:
    def __init__(self, owned=True):
        self.is_owner = owned


def _enabled_gate():
    gate = CommercialActivationGate()
    gate.enable()
    return gate


class OpenAIError(Exception):
    pass


class APIError(OpenAIError):
    pass


class APIConnectionError(APIError):
    pass


class APITimeoutError(APIConnectionError):
    pass


class APIStatusError(APIError):
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


class APIResponseValidationError(APIError):
    pass


class FakeHttpClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.close_count = 0
        self.close_error = None
        self.instances.append(self)

    def close(self):
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


@pytest.fixture(autouse=True)
def fake_openai_module(monkeypatch):
    FakeHttpClient.instances = []
    module = SimpleNamespace(OpenAI=lambda **kwargs: None,
                             DefaultHttpxClient=FakeHttpClient,
                             OpenAIError=OpenAIError,
                             APIError=APIError,
                             APIConnectionError=APIConnectionError,
                             APITimeoutError=APITimeoutError,
                             APIStatusError=APIStatusError,
                             APIResponseValidationError=APIResponseValidationError,
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
        self.clients = []

    def __call__(self, **kwargs):
        self.kwargs.append(kwargs)
        http_client = kwargs["http_client"]
        client = SimpleNamespace(responses=self.responses, close=http_client.close)
        self.clients.append(client)
        return client


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
    assert len(factory.clients) == FakeHttpClient.instances[0].close_count == 1
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
    assert FakeHttpClient.instances[0].close_count == 1


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
    http_client = factory.kwargs[0]["http_client"]
    assert http_client.kwargs["base_url"] == settings.base_url
    assert http_client.kwargs["timeout"] == factory.kwargs[0]["timeout"]
    assert set(http_client.kwargs) == {"base_url", "timeout", "event_hooks"}
    assert set(http_client.kwargs["event_hooks"]) == {"request", "response"}
    assert len(factory.clients) == http_client.close_count == 1
    call = factory.responses.calls[0]
    assert call["model"] == "gpt-6-sol"
    assert call["max_output_tokens"] == 900
    assert call["store"] is False
    assert 0 < call["timeout"] <= 60
    assert set(call) == {"model", "instructions", "input", "text", "max_output_tokens",
                         "store", "timeout"}
    assert call["instructions"] == _INSTRUCTIONS
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert call["text"]["format"]["schema"]["additionalProperties"] is False
    assert call["text"] == {"format": {"type": "json_schema",
                                      "name": "commercial_analysis_v1", "strict": True,
                                      "schema": response_schema()}}
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
    assert FakeHttpClient.instances[0].close_count == 1
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
    (APIStatusError(400), "provider_bad_request"),
])
def test_non_transient_errors_never_retry(error, code):
    factory = FakeFactory([error])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == code
    assert len(factory.responses.calls) == 1
    assert FakeHttpClient.instances[0].close_count == 1


def test_client_reused_across_retry_and_closed_only_after_final_attempt():
    factory = FakeFactory([APIConnectionError("synthetic"), _response()])
    close_counts_at_sleep = []

    def sleep(_delay):
        close_counts_at_sleep.append(FakeHttpClient.instances[0].close_count)

    assert isinstance(_adapter(factory=factory, sleep=sleep).analyze(_input()), AnalysisCandidates)
    assert len(factory.clients) == len(factory.kwargs) == 1
    assert len(factory.responses.calls) == 2
    assert close_counts_at_sleep == [0]
    assert FakeHttpClient.instances[0].close_count == 1


def test_client_closed_once_after_transient_exhaustion():
    factory = FakeFactory([APIConnectionError("first"), APIConnectionError("second")])
    with pytest.raises(OpenAIAnalysisError, match="provider_transient_exhausted"):
        _adapter(factory=factory, sleep=lambda _: None).analyze(_input())
    assert len(factory.clients) == 1
    assert len(factory.responses.calls) == 2
    assert FakeHttpClient.instances[0].close_count == 1


def test_successful_operation_with_close_failure_is_bounded_and_not_retried(capsys, caplog):
    caplog.set_level(logging.DEBUG)
    factory = FakeFactory()

    def close_failing_factory(**kwargs):
        kwargs["http_client"].close_error = RuntimeError("synthetic-secret-close")
        return factory(**kwargs)

    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=close_failing_factory).analyze(_input())
    assert caught.value.code == "provider_client_close_failure"
    assert len(factory.responses.calls) == 1
    assert FakeHttpClient.instances[0].close_count == 1
    captured = capsys.readouterr()
    assert "synthetic-secret-close" not in captured.out + captured.err + caplog.text + str(caught.value)


def test_primary_failure_survives_close_failure_without_retry(capsys, caplog):
    caplog.set_level(logging.DEBUG)
    factory = FakeFactory([APIStatusError(400)])

    def close_failing_factory(**kwargs):
        kwargs["http_client"].close_error = RuntimeError("synthetic-secret-close")
        return factory(**kwargs)

    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=close_failing_factory).analyze(_input())
    assert caught.value.code == "provider_bad_request"
    assert len(factory.responses.calls) == 1
    assert FakeHttpClient.instances[0].close_count == 1
    captured = capsys.readouterr()
    assert "synthetic-secret-close" not in captured.out + captured.err + caplog.text + str(caught.value)


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_factory_failure_closes_only_http_client_and_preserves_bounded_code(cleanup_fails):
    def failing_factory(**kwargs):
        if cleanup_fails:
            kwargs["http_client"].close_error = RuntimeError("synthetic-secret-close")
        raise RuntimeError("synthetic-secret-factory")

    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=failing_factory).analyze(_input())
    assert caught.value.code == "provider_unavailable"
    assert "synthetic-secret" not in str(caught.value)
    assert FakeHttpClient.instances[0].close_count == 1
    assert "synthetic-secret-and-body" not in str(caught.value)


@pytest.mark.parametrize("status, expected", [
    (400, "provider_bad_request"),
    (404, "provider_not_found"),
    (409, "provider_conflict"),
    (422, "provider_unprocessable"),
    (405, "provider_client_error"),
    (408, "provider_client_error"),
    (410, "provider_client_error"),
    (413, "provider_client_error"),
])
def test_typed_client_statuses_have_bounded_non_retryable_categories(
        status, expected, caplog):
    caplog.set_level(logging.DEBUG)
    error = APIStatusError(status, code="raw-provider-code\nsynthetic-secret-and-body")
    error.body = {"error": {"message": "raw-provider-body\nsynthetic-secret-and-body"}}
    error.url = "https://private.example/secret"
    factory = FakeFactory([error])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == expected
    assert len(factory.responses.calls) == 1
    for forbidden in ("raw-provider-code", "raw-provider-body", "synthetic-secret-and-body",
                      "private.example", "\n"):
        assert forbidden not in str(caught.value) + repr(caught.value) + caplog.text


@pytest.mark.parametrize("status", [True, "400", None, -1, 302, 600])
def test_malformed_or_unclassifiable_typed_status_remains_generic(status):
    factory = FakeFactory([APIStatusError(status)])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == "provider_failure"
    assert len(factory.responses.calls) == 1


@pytest.mark.parametrize("error, expected", [
    (APIResponseValidationError("raw-provider-body\nsynthetic-secret-and-body"),
     "provider_response_validation_failure"),
    (json.JSONDecodeError("raw-provider-body\nsynthetic-secret-and-body",
                          "https://private.example/secret", 0),
     "provider_response_json_failure"),
    (TypeError("raw-provider-body\nsynthetic-secret-and-body"),
     "provider_sdk_type_failure"),
    (ValueError("https://private.example/secret"), "provider_sdk_value_failure"),
    (RuntimeError("raw-provider-body\nsynthetic-secret-and-body"),
     "provider_sdk_runtime_failure"),
])
def test_exact_sdk_failures_are_bounded_and_non_retryable(error, expected, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    factory = FakeFactory([error])
    sleeps = []
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory, sleep=sleeps.append).analyze(_input())
    assert caught.value.code == expected
    assert len(factory.responses.calls) == 1
    assert sleeps == []
    captured = capsys.readouterr()
    bounded = str(caught.value) + repr(caught.value) + captured.out + captured.err + caplog.text
    for forbidden in ("raw-provider-body", "synthetic-secret-and-body", "private.example",
                      "\n"):
        assert forbidden not in bounded
    assert isinstance(_adapter(factory=FakeFactory()).analyze(_input()), AnalysisCandidates)


class CustomValidationError(APIResponseValidationError):
    pass


class CustomJSONDecodeError(json.JSONDecodeError):
    pass


class CustomTypeError(TypeError):
    pass


class CustomValueError(ValueError):
    pass


class CustomRuntimeError(RuntimeError):
    pass


class UnrelatedError(Exception):
    pass


@pytest.mark.parametrize("error, expected", [
    (OpenAIError("synthetic-secret"), "provider_openai_error_family"),
    (APIError("synthetic-secret"), "provider_openai_error_family"),
    (CustomValidationError("synthetic-secret"), "provider_openai_error_family"),
    (httpx2.RequestError("synthetic-secret"), "provider_http_client_error_family"),
    (httpx2.ProtocolError("synthetic-secret"), "provider_http_client_error_family"),
    (httpx2.DecodingError("synthetic-secret"), "provider_http_client_error_family"),
    (OSError("synthetic-secret"), "provider_os_error_family"),
    (ssl.SSLCertVerificationError("synthetic-secret"), "provider_os_error_family"),
    (UnicodeError("synthetic-secret"), "provider_unicode_before_request_hook"),
    (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "synthetic-secret"),
     "provider_unicode_before_request_hook"),
    (UnicodeEncodeError("utf-8", "\ud800", 0, 1, "synthetic-secret"),
     "provider_unicode_before_request_hook"),
    (idna.IDNAError("synthetic-secret"), "provider_unicode_before_request_hook"),
    (pydantic.ValidationError.from_exception_data(
        "Synthetic", [{"type": "missing", "loc": ("field",), "input": {}}]),
     "provider_value_subclass_family"),
    (pydantic_core.PydanticSerializationError("synthetic-secret"),
     "provider_value_subclass_family"),
    (CustomJSONDecodeError("synthetic-secret", "synthetic-document", 0),
     "provider_value_subclass_family"),
    (CustomValueError("synthetic-secret"), "provider_value_subclass_family"),
    (CustomTypeError("synthetic-secret"), "provider_python_internal_family"),
    (CustomRuntimeError("synthetic-secret"), "provider_python_internal_family"),
    (AttributeError("synthetic-secret"), "provider_python_internal_family"),
    (KeyError("synthetic-secret"), "provider_python_internal_family"),
    (IndexError("synthetic-secret"), "provider_python_internal_family"),
    (AssertionError("synthetic-secret"), "provider_python_internal_family"),
    (ExceptionGroup("synthetic-secret", [ValueError("synthetic-secret")]),
     "provider_exception_group_family"),
    (httpcore2.ConnectError("synthetic-secret"), "provider_non_http_failure"),
    (UnrelatedError("synthetic-secret"), "provider_non_http_failure"),
])
def test_residual_sdk_error_families_are_bounded_and_non_retryable(
        error, expected, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    factory = FakeFactory([error])
    sleeps = []
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory, sleep=sleeps.append).analyze(_input())
    assert caught.value.code == expected
    assert len(factory.responses.calls) == 1
    assert sleeps == []
    captured = capsys.readouterr()
    bounded = str(caught.value) + repr(caught.value) + captured.out + captured.err + caplog.text
    assert "synthetic-secret" not in bounded
    assert isinstance(_adapter(factory=FakeFactory()).analyze(_input()), AnalysisCandidates)


@pytest.mark.parametrize("events, expected", [
    ((), "provider_unicode_before_request_hook"),
    (("request",), "provider_unicode_request_hook_reached"),
    (("request", "response", "request", "response"),
     "provider_unicode_response_hook_reached"),
])
def test_unicode_hook_phases_are_monotonic_and_ignore_arguments(events, expected):
    class Opaque:
        def __getattribute__(self, _name):
            raise AssertionError("hook accessed its argument")

    factory = FakeFactory()

    class HookResponses(FakeResponses):
        def create(self, **kwargs):
            self.calls.append(kwargs)
            hooks = factory.kwargs[0]["http_client"].kwargs["event_hooks"]
            for event in events:
                hooks[event][0](Opaque())
            raise UnicodeError("synthetic-secret")

    factory.responses = HookResponses()
    sleeps = []
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory, sleep=sleeps.append).analyze(_input())
    assert caught.value.code == expected
    assert len(factory.responses.calls) == 1
    assert sleeps == []
    assert FakeHttpClient.instances[0].close_count == 1


def test_unicode_phase_resets_before_second_adapter_attempt():
    factory = FakeFactory()

    class HookResponses(FakeResponses):
        def create(self, **kwargs):
            self.calls.append(kwargs)
            hooks = factory.kwargs[0]["http_client"].kwargs["event_hooks"]
            if len(self.calls) == 1:
                hooks["response"][0](object())
                raise APIConnectionError("synthetic-secret")
            raise UnicodeError("synthetic-secret")

    factory.responses = HookResponses()
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory, sleep=lambda _: None).analyze(_input())
    assert caught.value.code == "provider_unicode_before_request_hook"
    assert len(factory.responses.calls) == 2
    assert FakeHttpClient.instances[0].close_count == 1


def test_unicode_phase_unknown_state_keeps_family_fallback():
    from app.integrations.openai_analysis import _unicode_phase_code

    assert _unicode_phase_code(None) == "provider_unicode_error_family"
    assert _unicode_phase_code("unrecognized") == "provider_unicode_error_family"


def test_raw_http_status_error_is_not_broadly_classified_as_request_error():
    request = httpx2.Request("GET", "https://synthetic.invalid/v1/responses")
    response = httpx2.Response(400, request=request)
    factory = FakeFactory([httpx2.HTTPStatusError(
        "synthetic-secret", request=request, response=response,
    )])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == "provider_non_http_failure"
    assert len(factory.responses.calls) == 1


@pytest.mark.parametrize("forged_status", [400, 429, 503])
def test_non_http_exception_cannot_forge_status_classification(forged_status):
    class ForgedStatusError(Exception):
        status_code = forged_status

    factory = FakeFactory([ForgedStatusError("raw-provider-body")])
    with pytest.raises(OpenAIAnalysisError) as caught:
        _adapter(factory=factory).analyze(_input())
    assert caught.value.code == "provider_non_http_failure"
    assert len(factory.responses.calls) == 1
    assert "raw-provider-body" not in str(caught.value)


def test_local_schema_construction_failure_is_bounded_without_sdk_call_or_retry(
        monkeypatch, capsys, caplog):
    import app.integrations.openai_analysis as adapter_module

    caplog.set_level(logging.DEBUG)
    original_schema = adapter_module.response_schema
    sleeps = []

    def broken_schema():
        raise TypeError("raw-provider-body\nsynthetic-secret-and-body "
                        "https://private.example/secret C:/private/credential.txt")

    monkeypatch.setattr(adapter_module, "response_schema", broken_schema)
    factory = FakeFactory()
    adapter = _adapter(factory=factory, sleep=sleeps.append)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.analyze(_input())
    assert caught.value.code == "request_schema_failure"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert factory.responses.calls == []
    assert sleeps == []
    captured = capsys.readouterr()
    bounded = str(caught.value) + repr(caught.value) + captured.out + captured.err + caplog.text
    for forbidden in ("raw-provider-body", "synthetic-secret-and-body", "private.example",
                      "C:/private/credential.txt", "\n"):
        assert forbidden not in bounded
    monkeypatch.setattr(adapter_module, "response_schema", original_schema)
    assert isinstance(adapter.analyze(_input()), AnalysisCandidates)
    assert len(factory.responses.calls) == 1


def test_transient_retry_rebuilds_schema_and_reauthorizes(monkeypatch):
    import app.integrations.openai_analysis as adapter_module

    original_schema = adapter_module.response_schema
    schema_calls = []

    def counted_schema():
        schema_calls.append(True)
        return original_schema()

    class CountingOwnership:
        checks = 0

        @property
        def is_owner(self):
            self.checks += 1
            return True

    class CountingGate:
        checks = 0

        @property
        def is_enabled(self):
            self.checks += 1
            return True

    monkeypatch.setattr(adapter_module, "response_schema", counted_schema)
    factory = FakeFactory([APIConnectionError("synthetic"), _response()])
    ownership, gate = CountingOwnership(), CountingGate()
    adapter = _adapter(factory=factory, ownership=ownership, commercial_gate=gate,
                       sleep=lambda _: None)
    assert isinstance(adapter.analyze(_input()), AnalysisCandidates)
    assert len(schema_calls) == len(factory.responses.calls) == 2
    assert ownership.checks == gate.checks == 3
    first, second = factory.responses.calls
    assert {key: value for key, value in first.items() if key != "timeout"} == {
        key: value for key, value in second.items() if key != "timeout"
    }
    assert 0 < second["timeout"] <= first["timeout"] <= 60


def test_fixed_smoke_request_serializes_with_pinned_sdk_and_no_network(monkeypatch):
    assert installed_openai.__version__ == "3.17.0"
    monkeypatch.setitem(sys.modules, "openai", installed_openai)
    seen = []

    def no_send(request):
        body = json.loads(request.content)
        seen.append((request.method, request.url.path, body))
        return httpx2.Response(200, json={"id": "resp_synthetic", "object": "response",
                                          "status": "completed", "output": []})

    settings = AISettings(enabled=True, model="gpt-6-sol",
                          base_url="https://api.openai.com/v1", max_output_tokens=4096)
    credentials = FakeCredentials("synthetic-offline-only")
    def fake_http_client(**kwargs):
        return httpx2.Client(**kwargs, transport=httpx2.MockTransport(no_send),
                             trust_env=False)

    monkeypatch.setattr(installed_openai, "DefaultHttpxClient", fake_http_client)

    def factory(**kwargs):
        assert kwargs["api_key"] == "synthetic-offline-only"
        assert kwargs["max_retries"] == 0
        return installed_openai.OpenAI(**kwargs)

    adapter = OpenAIAnalysis(settings, credentials, ownership=FakeOwnership(),
                             client_factory=factory)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.smoke()
    assert caught.value.code == "invalid_output"
    assert len(seen) == 1
    method, path, body = seen[0]
    assert (method, path) == ("POST", "/v1/responses")
    assert set(body) == {"model", "instructions", "input", "text", "max_output_tokens",
                         "store"}
    assert body["model"] == "gpt-6-sol"
    assert body["instructions"] == _INSTRUCTIONS
    assert body["input"] == [{"role": "user", "content": json.dumps(
        {"messages": project_analysis_input(_fixed_smoke_input()).remote_payload()},
        ensure_ascii=False, separators=(",", ":"))}]
    assert body["text"] == {"format": {"type": "json_schema",
                                      "name": "commercial_analysis_v1", "strict": True,
                                      "schema": response_schema()}}
    assert body["max_output_tokens"] == 4096
    assert body["store"] is False


def _pinned_sdk_smoke_failure(monkeypatch, responder, *, strict=False,
                              http_client_type=httpx2.Client,
                              secret="synthetic-offline-only"):
    monkeypatch.setitem(sys.modules, "openai", installed_openai)
    seen = []

    def no_send(request):
        seen.append((request.method, request.url.path))
        return responder(request)

    settings = AISettings(enabled=True, model="gpt-6-sol",
                          base_url="https://api.openai.com/v1", max_output_tokens=4096)
    def fake_http_client(**kwargs):
        return http_client_type(**kwargs, transport=httpx2.MockTransport(no_send),
                                trust_env=False)

    monkeypatch.setattr(installed_openai, "DefaultHttpxClient", fake_http_client)

    def factory(**kwargs):
        assert kwargs["api_key"] == secret
        assert kwargs["max_retries"] == 0
        return installed_openai.OpenAI(
            **kwargs, _strict_response_validation=strict,
        )

    adapter = OpenAIAnalysis(settings, FakeCredentials(secret),
                             ownership=FakeOwnership(), client_factory=factory,
                             sleep=lambda _: None)
    with pytest.raises(OpenAIAnalysisError) as caught:
        adapter.smoke()
    return caught.value.code, seen


def test_pinned_sdk_malformed_json_is_bounded_without_network(monkeypatch):
    code, seen = _pinned_sdk_smoke_failure(
        monkeypatch,
        lambda _request: httpx2.Response(
            200, content=b"{synthetic-invalid", headers={"content-type": "application/json"}),
    )
    assert code == "provider_response_json_failure"
    assert seen == [("POST", "/v1/responses")]


@pytest.mark.parametrize("payload", [
    b"\xff",
    bytes.fromhex("fffe7b00ff"),
    bytes.fromhex("fffe00007b0000"),
])
def test_pinned_sdk_invalid_unicode_is_response_phase_without_network(monkeypatch, payload):
    code, seen = _pinned_sdk_smoke_failure(
        monkeypatch,
        lambda _request: httpx2.Response(
            200, content=payload, headers={"content-type": "application/json"}),
    )
    assert code == "provider_unicode_response_hook_reached"
    assert seen == [("POST", "/v1/responses")]


def test_pinned_sdk_pre_hook_unicode_uses_bounded_phase_without_network(monkeypatch):
    code, seen = _pinned_sdk_smoke_failure(
        monkeypatch,
        lambda _request: pytest.fail("mock transport reached"),
        secret="synthetic-\u2603",
    )
    assert code == "provider_unicode_before_request_hook"
    assert seen == []


def test_pinned_sdk_request_hook_without_response_is_bounded(monkeypatch):
    def fail(_request):
        raise UnicodeError("synthetic-secret")

    code, seen = _pinned_sdk_smoke_failure(monkeypatch, fail)
    assert code == "provider_unicode_request_hook_reached"
    assert seen == [("POST", "/v1/responses")]


def test_pinned_sdk_strict_validation_is_bounded_without_network(monkeypatch):
    code, seen = _pinned_sdk_smoke_failure(
        monkeypatch, lambda _request: httpx2.Response(200, json={}), strict=True,
    )
    assert code == "provider_response_validation_failure"
    assert seen == [("POST", "/v1/responses")]


def test_pinned_sdk_pre_send_type_failure_has_zero_dispatch(monkeypatch):
    class BrokenBuildClient(httpx2.Client):
        def build_request(self, *args, **kwargs):
            raise TypeError("synthetic-secret-and-body")

    code, seen = _pinned_sdk_smoke_failure(
        monkeypatch, lambda _request: pytest.fail("mock transport reached"),
        http_client_type=BrokenBuildClient,
    )
    assert code == "provider_sdk_type_failure"
    assert seen == []


def test_pinned_sdk_pre_send_structural_family_has_zero_dispatch(monkeypatch):
    class BrokenBuildClient(httpx2.Client):
        def build_request(self, *args, **kwargs):
            raise AttributeError("synthetic-secret-and-body")

    code, seen = _pinned_sdk_smoke_failure(
        monkeypatch, lambda _request: pytest.fail("mock transport reached"),
        http_client_type=BrokenBuildClient,
    )
    assert code == "provider_python_internal_family"
    assert seen == []


@pytest.mark.parametrize("error, expected", [
    (installed_openai.OpenAIError("synthetic-secret-and-body"),
     "provider_openai_error_family"),
    (OSError("synthetic-secret-and-body"), "provider_os_error_family"),
    (AttributeError("synthetic-secret-and-body"), "provider_python_internal_family"),
    (httpcore2.ConnectError("synthetic-secret-and-body"),
     "provider_non_http_failure"),
])
def test_pinned_sdk_injected_residual_families_stay_bounded_without_network(
        monkeypatch, error, expected):
    def fail(_request):
        raise error

    code, seen = _pinned_sdk_smoke_failure(monkeypatch, fail)
    assert code == expected
    assert seen == [("POST", "/v1/responses")]


@pytest.mark.parametrize("error, expected", [
    (ValueError("synthetic-secret-and-body"), "provider_sdk_value_failure"),
    (RuntimeError("synthetic-secret-and-body"), "provider_sdk_runtime_failure"),
])
def test_pinned_sdk_non_request_transport_exception_stays_bounded(
        monkeypatch, error, expected):
    def fail(_request):
        raise error

    code, seen = _pinned_sdk_smoke_failure(monkeypatch, fail)
    assert code == expected
    assert seen == [("POST", "/v1/responses")]


@pytest.mark.parametrize("error_type, expected", [
    (httpx2.ConnectError, "provider_transient_exhausted"),
    (httpx2.ConnectTimeout, "timeout"),
    (httpx2.ProxyError, "provider_transient_exhausted"),
    (httpx2.DecodingError, "provider_transient_exhausted"),
])
def test_pinned_sdk_transport_errors_keep_existing_categories(
        monkeypatch, error_type, expected):
    def fail(request):
        raise error_type("synthetic-secret-and-body", request=request)

    code, seen = _pinned_sdk_smoke_failure(monkeypatch, fail)
    assert code == expected
    assert seen == [("POST", "/v1/responses")] * 2


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
