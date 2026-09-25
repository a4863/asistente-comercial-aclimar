import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.integrations.openai_analysis import OpenAIAnalysis
from app.persistence.database import make_session_factory
from app.security.session import issue_csrf_token, require_local_host, validate_protected_request
from app.services.email_analysis import (
    AnalysisServiceError, analyze_email_in_thread, list_manual_analysis_options,
)

router = APIRouter(dependencies=[Depends(require_local_host)])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
_PRIVATE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
_RESULT_CODES = {
    "completed": 200, "completed_replay": 200, "in_progress": 202,
    "retry_required": 409, "retry_not_available": 409, "blocked": 403,
    "invalid_request": 400, "invalid_target": 404, "unavailable": 503,
    "disabled": 503, "credential_missing": 503, "credential_unavailable": 503,
    "no_analyzable_body": 422, "failed_retryable": 200,
    "stale_retryable": 200, "invalid_security": 403,
}


def _result(code: str) -> JSONResponse:
    bounded = code if code in _RESULT_CODES else "unavailable"
    return JSONResponse({"status": bounded}, status_code=_RESULT_CODES[bounded],
                        headers=_PRIVATE_HEADERS)


def _operational_lock(application):
    try:
        lock = application.state.operational_lock
        if application.state.operational_ready is True and lock is not None and lock.is_owner is True:
            return lock
    except Exception:
        pass
    return None


async def _target_id(request: Request) -> int | None:
    content_type = request.headers.get("content-type", "").lower().replace(" ", "")
    if content_type not in {"application/json", "application/json;charset=utf-8"}:
        return None
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > 256:
                return None
            body.extend(chunk)

        def unique_object(pairs):
            if len(pairs) != len({key for key, _ in pairs}):
                raise ValueError("duplicate_key")
            return dict(pairs)

        data = json.loads(body.decode("utf-8"), object_pairs_hook=unique_object)
    except (ValueError, UnicodeError):
        return None
    if not isinstance(data, dict) or set(data) != {"source_record_id"}:
        return None
    source_id = data["source_record_id"]
    return source_id if type(source_id) is int and 0 < source_id <= 2**63 - 1 else None


async def _manual_analysis(request: Request, intent: str) -> JSONResponse:
    if not validate_protected_request(request, request.headers.get("x-csrf-token")):
        return _result("invalid_security")
    application = request.app
    lock = _operational_lock(application)
    if lock is None:
        return _result("unavailable")
    try:
        if application.state.commercial_gate.is_enabled is not True:
            return _result("blocked")
    except Exception:
        return _result("blocked")
    ai = application.state.settings.ai
    if ai.enabled is not True:
        return _result("disabled")
    try:
        presence = application.state.credential_store.credential_presence(
            ai.credential_service, ai.credential_account)
    except Exception:
        presence = "unavailable"
    if presence != "present":
        return _result("credential_missing" if presence == "missing"
                       else "credential_unavailable")
    source_id = await _target_id(request)
    if source_id is None:
        return _result("invalid_request")
    try:
        adapter = OpenAIAnalysis(ai, application.state.credential_store,
                                 ownership=lock,
                                 commercial_gate=application.state.commercial_gate)
        factory = make_session_factory(application.state.settings.database_url)
        try:
            analysis = analyze_email_in_thread(
                factory, adapter, application.state.settings.imap.account_scope,
                source_id, request_mode="manual", force_reanalysis=False,
                manual_intent=intent)
        finally:
            factory.kw["bind"].dispose()
        return _result(analysis.status)
    except AnalysisServiceError as error:
        return _result("invalid_target" if error.code == "invalid_target" else "unavailable")
    except Exception:
        return _result("unavailable")

@router.get("/health")
def health(): return {"status": "ok"}

@router.get("/", response_class=HTMLResponse)
def status(request: Request):
    application = request.app
    ai = application.state.settings.ai
    endpoint = {"https://api.openai.com/v1": "global",
                "https://eu.api.openai.com/v1": "eu"}.get(ai.base_url, "unknown")
    try:
        credential = application.state.credential_store.credential_presence(
            ai.credential_service, ai.credential_account)
    except Exception:
        credential = "unavailable"
    if credential not in ("present", "missing", "unavailable"):
        credential = "unavailable"
    try:
        authorized = application.state.commercial_gate.is_enabled is True
    except Exception:
        authorized = False
    operational = _operational_lock(application) is not None
    options = ()
    token = None
    if operational:
        try:
            factory = make_session_factory(application.state.settings.database_url)
            try:
                options = list_manual_analysis_options(
                    factory, application.state.settings.imap.account_scope)
            finally:
                factory.kw["bind"].dispose()
            if any(option.state in {"ready", "retry_required"} for option in options):
                token = issue_csrf_token(request.session)
        except Exception:
            options = ()
            token = None
    return templates.TemplateResponse(request, "status.html", {
        "status": "ok", "ai_state": "enabled" if ai.enabled else "disabled",
        "provider": ai.provider, "model": ai.model, "endpoint": endpoint,
        "credential": credential, "commercial": "authorized" if authorized else "blocked",
        "operational": "ready" if operational else "inactive", "smoke": "pending",
        "options": options, "action_token": token,
    }, headers=_PRIVATE_HEADERS)


@router.post("/analysis/email")
async def analyze_email(request: Request):
    return await _manual_analysis(request, "initial")


@router.post("/analysis/email/retry")
async def retry_email_analysis(request: Request):
    return await _manual_analysis(request, "retry")
