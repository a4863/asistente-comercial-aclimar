import hmac
import secrets
from collections.abc import MutableMapping


CSRF_SESSION_KEY = "csrf_token"


def issue_csrf_token(session: MutableMapping[str, str]) -> str:
    token = session.get(CSRF_SESSION_KEY)
    if token is None:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(session: MutableMapping[str, str], supplied_token: str | None) -> bool:
    expected_token = session.get(CSRF_SESSION_KEY)
    return bool(expected_token and supplied_token and hmac.compare_digest(expected_token, supplied_token))
