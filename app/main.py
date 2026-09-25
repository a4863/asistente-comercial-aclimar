from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from app.config import Settings, load_settings
from app.security.single_instance import SingleInstanceLock
from app.web.routes import router


@asynccontextmanager
async def _operational_lifespan(app: FastAPI):
    lock = SingleInstanceLock(app.state.settings.database_url)
    lock.acquire()
    try:
        app.state.operational_lock = lock
        yield
    finally:
        app.state.operational_lock = None
        lock.close()


def create_app(settings: Settings | None = None, *, _operational: bool = False) -> FastAPI:
    configured_settings = settings or load_settings()
    if configured_settings.host != "127.0.0.1":
        raise ValueError("The application must bind only to 127.0.0.1")
    app = FastAPI(title="Asistente Comercial ACLIMAR",
                  lifespan=_operational_lifespan if _operational else None)
    app.state.settings = configured_settings
    app.state.operational_lock = None
    app.include_router(router)
    return app


def run(settings: Settings | None = None) -> None:
    configured_settings = settings or load_settings()
    application = create_app(configured_settings, _operational=True)
    uvicorn.run(application, host=configured_settings.host, port=configured_settings.port,
                reload=False, workers=1, lifespan="on")


app = create_app()
