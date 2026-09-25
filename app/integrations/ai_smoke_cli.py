"""Explicit one-shot synthetic OpenAI smoke command; never reads commercial data."""

import sys

from app.config import load_settings
from app.integrations.openai_analysis import OpenAIAnalysis, OpenAIAnalysisError
from app.security.credentials import KeyringCredentialStore
from app.security.single_instance import SingleInstanceError, SingleInstanceLock


_USAGE = "Usage: asistente-aclimar-ai-smoke"


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--help"]:
        print(_USAGE)
        return 0
    if arguments:
        print("invalid_command", file=sys.stderr)
        return 2
    try:
        settings = load_settings()
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
    except OpenAIAnalysisError:
        print("smoke_failed")
        return 1
    except Exception:
        print("unavailable")
        return 1
    print("passed" if result == "passed" else "smoke_failed")
    return 0 if result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
