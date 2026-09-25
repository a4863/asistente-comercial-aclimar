from contextlib import asynccontextmanager
import secrets

from fastapi import FastAPI
import uvicorn

from app.config import RuntimeConfigError, Settings, load_operational_settings, load_settings
from app.persistence.database import make_session_factory
from app.persistence.repositories import AnalysisRepository
from app.security.activation import CommercialActivationGate
from app.security.credentials import KeyringCredentialStore
from app.security.single_instance import SingleInstanceLock
from app.security.session import LocalSessionMiddleware
from app.web.routes import router


@asynccontextmanager
async def _operational_lifespan(app: FastAPI):
    lock = SingleInstanceLock(app.state.settings.database_url)
    lock.acquire()
    try:
        if not lock.is_owner:
            raise RuntimeError("operational_lock_unavailable")
        app.state.operational_lock = lock
        try:
            factory = make_session_factory(app.state.settings.database_url)
            try:
                with factory.begin() as session:
                    AnalysisRepository(session).establish_cutover_or_recover()
            finally:
                factory.kw["bind"].dispose()
        except Exception:
            raise RuntimeError("startup_recovery_failed") from None
        if not lock.is_owner:
            raise RuntimeError("operational_lock_unavailable")
        app.state.operational_ready = True
        yield
    finally:
        app.state.operational_ready = False
        app.state.operational_lock = None
        lock.close()


def create_app(settings: Settings | None = None, *, _operational: bool = False) -> FastAPI:
    configured_settings = settings or load_settings()
    if configured_settings.host != "127.0.0.1":
        raise ValueError("The application must bind only to 127.0.0.1")
    app = FastAPI(title="Asistente Comercial ACLIMAR",
                  lifespan=_operational_lifespan if _operational else None)
    app.add_middleware(LocalSessionMiddleware, secret_key=secrets.token_urlsafe(32))
    app.state.settings = configured_settings
    app.state.operational_lock = None
    app.state.operational_ready = False
    app.state.commercial_gate = CommercialActivationGate()
    app.state.credential_store = KeyringCredentialStore()
    app.include_router(router)
    return app


def run(settings: Settings | None = None) -> None:
    if settings is None:
        try:
            configured_settings = load_operational_settings()
        except RuntimeConfigError:
            raise SystemExit("configuration_unavailable") from None
    else:
        configured_settings = settings
    application = create_app(configured_settings, _operational=True)
    uvicorn.run(application, host=configured_settings.host, port=configured_settings.port,
                reload=False, workers=1, lifespan="on")


app = create_app()
