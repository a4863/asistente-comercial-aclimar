import hmac
import base64
import binascii
import hashlib
import json
import secrets
import time
from collections.abc import MutableMapping
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


CSRF_SESSION_KEY = "csrf_token"
SESSION_COOKIE = "aclimar_session"
SESSION_MAX_AGE = 1800


class LocalSessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, secret_key: str):
        super().__init__(app)
        self._secret = secret_key.encode("utf-8")

    def _decode(self, raw: str) -> dict[str, str]:
        try:
            payload, timestamp, signature = raw.split(".")
            signed = f"{payload}.{timestamp}".encode("ascii")
            expected = hmac.new(self._secret, signed, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return {}
            issued_at = int(timestamp)
            now = int(time.time())
            if issued_at > now or now - issued_at >= SESSION_MAX_AGE:
                return {}
            decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if not isinstance(decoded, dict) or any(
                    not isinstance(key, str) or not isinstance(value, str)
                    for key, value in decoded.items()):
                return {}
            return decoded
        except (ValueError, TypeError, UnicodeError, binascii.Error):
            return {}

    def _encode(self, session: dict[str, str]) -> str:
        payload = base64.urlsafe_b64encode(json.dumps(session, sort_keys=True,
                                                       separators=(",", ":")).encode()).decode().rstrip("=")
        timestamp = str(int(time.time()))
        signed = f"{payload}.{timestamp}"
        signature = hmac.new(self._secret, signed.encode("ascii"), hashlib.sha256).hexdigest()
        return f"{signed}.{signature}"

    async def dispatch(self, request: Request, call_next):
        cookies = SimpleCookie()
        try:
            cookies.load(request.headers.get("cookie", ""))
            raw = cookies[SESSION_COOKIE].value if SESSION_COOKIE in cookies else ""
        except CookieError:
            raw = ""
        original = self._decode(raw) if raw else {}
        request.scope["session"] = original.copy()
        response = await call_next(request)
        current = request.scope["session"]
        if current and current != original:
            response.set_cookie(SESSION_COOKIE, self._encode(current), max_age=SESSION_MAX_AGE,
                                httponly=True, samesite="strict", secure=False, path="/")
        elif not current and raw:
            response.delete_cookie(SESSION_COOKIE, path="/")
        return response


def issue_csrf_token(session: MutableMapping[str, str]) -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(session: MutableMapping[str, str], supplied_token: str | None) -> bool:
    expected_token = session.get(CSRF_SESSION_KEY)
    return (isinstance(expected_token, str) and bool(expected_token)
            and isinstance(supplied_token, str) and bool(supplied_token)
            and hmac.compare_digest(expected_token, supplied_token))


def _local_authority(authority: str | None, port: int, *, test_client: bool = False) -> tuple[str, int] | None:
    if not isinstance(authority, str) or not authority or any(
            character in authority for character in "@/?#\\% \t\r\n"):
        return None
    parts = authority.split(":")
    if len(parts) > 2:
        return None
    host = parts[0].lower()
    if host not in ("127.0.0.1", "localhost") and not (test_client and host == "testserver"):
        return None
    if len(parts) == 1:
        if host == "testserver" and test_client:
            return host, 80
        return (host, 80) if port == 80 else None
    if (not 1 <= len(parts[1]) <= 5 or not parts[1].isascii()
            or not parts[1].isdecimal() or parts[1].startswith("0")):
        return None
    supplied_port = int(parts[1])
    if not 1 <= supplied_port <= 65535 or supplied_port != port:
        return None
    return host, supplied_port


def valid_local_host(request: Request) -> bool:
    client = request.client
    return _local_authority(request.headers.get("host"), request.app.state.settings.port,
                            test_client=client is not None and client.host == "testclient") is not None


def require_local_host(request: Request) -> None:
    if not valid_local_host(request):
        raise HTTPException(status_code=400, detail="invalid_host")


def valid_local_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin or origin == "null":
        return False
    try:
        parsed = urlsplit(origin)
        if (parsed.scheme != "http" or not parsed.netloc or parsed.path or parsed.query
                or parsed.fragment or parsed.username is not None or parsed.password is not None):
            return False
        host = _local_authority(request.headers.get("host"), request.app.state.settings.port,
                                test_client=request.client is not None
                                and request.client.host == "testclient")
        origin_host = _local_authority(parsed.netloc, request.app.state.settings.port,
                                       test_client=request.client is not None
                                       and request.client.host == "testclient")
        return host is not None and origin_host == host
    except ValueError:
        return False


def validate_protected_request(request: Request, supplied_token: str | None) -> bool:
    return (valid_local_host(request) and valid_local_origin(request)
            and validate_csrf_token(request.session, supplied_token))
