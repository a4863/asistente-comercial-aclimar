from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

@router.get("/health")
def health(): return {"status": "ok"}

@router.get("/", response_class=HTMLResponse)
def status(request: Request): return templates.TemplateResponse(request, "status.html", {"status": "ok"})
