from fastapi import FastAPI
import uvicorn

from app.config import Settings, load_settings
from app.web.routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or load_settings()
    if configured_settings.host != "127.0.0.1":
        raise ValueError("The application must bind only to 127.0.0.1")
    app = FastAPI(title="Asistente Comercial ACLIMAR")
    app.state.settings = configured_settings
    app.include_router(router)
    return app


def run(settings: Settings | None = None) -> None:
    configured_settings = settings or load_settings()
    application = create_app(configured_settings)
    uvicorn.run(application, host=configured_settings.host, port=configured_settings.port)


app = create_app()
