"""Explicit one-shot synthetic OpenAI smoke command; never reads commercial data."""

import sys

from app.config import load_operational_settings
from app.integrations.openai_analysis import OpenAIAnalysis, OpenAIAnalysisError
from app.security.credentials import KeyringCredentialStore
from app.security.single_instance import SingleInstanceError, SingleInstanceLock


_USAGE = "Usage: asistente-aclimar-ai-smoke"
_DIAGNOSTIC_CODES = frozenset({
    "credential_missing",
    "credential_unavailable",
    "provider_unavailable",
    "provider_auth",
    "provider_quota",
    "provider_transient_exhausted",
    "provider_failure",
    "timeout",
    "provider_incomplete",
    "provider_refusal",
    "invalid_output",
    "invalid_configuration",
    "provider_bad_request",
    "provider_not_found",
    "provider_conflict",
    "provider_unprocessable",
    "provider_client_error",
    "provider_non_http_failure",
    "request_schema_failure",
    "provider_response_validation_failure",
    "provider_response_json_failure",
    "provider_sdk_type_failure",
    "provider_sdk_value_failure",
    "provider_sdk_runtime_failure",
    "provider_openai_error_family",
    "provider_http_client_error_family",
    "provider_os_error_family",
    "provider_unicode_error_family",
    "provider_value_subclass_family",
    "provider_python_internal_family",
    "provider_exception_group_family",
})


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--help"]:
        print(_USAGE)
        return 0
    if arguments:
        print("invalid_command", file=sys.stderr)
        return 2
    try:
        settings = load_operational_settings()
    except Exception:
        print("unavailable")
        return 1
    if not settings.ai.enabled:
        print("disabled")
        return 1
    try:
        with SingleInstanceLock(settings.database_url) as lock:
            adapter = OpenAIAnalysis(settings.ai, KeyringCredentialStore(), ownership=lock)
            result = adapter.smoke()
    except SingleInstanceError:
        print("lock_unavailable")
        return 1
    except OpenAIAnalysisError as error:
        code = error.code
        if type(code) is str and code in _DIAGNOSTIC_CODES:
            print(f"smoke_failed:{code}")
        else:
            print("smoke_failed")
        return 1
    except Exception:
        print("unavailable")
        return 1
    print("passed" if result == "passed" else "smoke_failed")
    return 0 if result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
