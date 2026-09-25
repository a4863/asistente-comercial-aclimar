from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

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
    try:
        lock = application.state.operational_lock
        operational = (application.state.operational_ready is True and
                       lock is not None and lock.is_owner is True)
    except Exception:
        operational = False
    return templates.TemplateResponse(request, "status.html", {
        "status": "ok", "ai_state": "enabled" if ai.enabled else "disabled",
        "provider": ai.provider, "model": ai.model, "endpoint": endpoint,
        "credential": credential, "commercial": "authorized" if authorized else "blocked",
        "operational": "ready" if operational else "inactive", "smoke": "pending",
    })
